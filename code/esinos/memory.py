"""Pagination, remplacement de pages, TLB et EAT pour ESINOS."""

from __future__ import annotations

from collections import OrderedDict, deque
from dataclasses import dataclass
from math import isfinite
from typing import Deque, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


class VirtualMemoryError(ValueError):
    """Erreur de validation ou de traduction dans le simulateur memoire."""


@dataclass(frozen=True)
class ReplacementStep:
    """Etat des cadres apres une reference de page."""

    index: int
    page: int
    frames: Tuple[Optional[int], ...]
    hit: bool
    evicted: Optional[int]


@dataclass(frozen=True)
class PageReplacementResult:
    """Trace complete d'un algorithme de remplacement."""

    algorithm: str
    frame_count: int
    references: Tuple[int, ...]
    steps: Tuple[ReplacementStep, ...]
    page_faults: int

    @property
    def hits(self) -> int:
        return len(self.references) - self.page_faults

    @property
    def fault_rate(self) -> float:
        return self.page_faults / len(self.references) if self.references else 0.0


@dataclass(frozen=True)
class AddressTranslation:
    """Resultat d'une traduction logique vers une adresse physique."""

    logical_address: int
    page: int
    offset: int
    frame: Optional[int]
    physical_address: Optional[int]
    tlb_hit: bool
    page_fault: bool


def _validate_references(references: Iterable[int], frame_count: int) -> List[int]:
    if frame_count <= 0:
        raise VirtualMemoryError("Le nombre de cadres doit etre strictement positif.")
    sequence = list(references)
    if not sequence:
        raise VirtualMemoryError("La chaine de references est vide.")
    if any(not isinstance(page, int) or page < 0 for page in sequence):
        raise VirtualMemoryError("Les references doivent etre des entiers positifs ou nuls.")
    return sequence


def simulate_page_replacement(
    references: Iterable[int], frame_count: int, algorithm: str
) -> PageReplacementResult:
    """Simule FIFO, LRU ou Optimal et conserve chaque etape visible.

    ``frames`` est une liste de cadres physiques. Les algorithmes ne
    manipulent que des numeros de page : cette simulation est independante de
    la traduction d'adresses, ce qui facilite l'explication en soutenance.
    """

    sequence = _validate_references(references, frame_count)
    normalized = algorithm.lower().strip().replace("_", "")
    aliases = {"fifo": "FIFO", "lru": "LRU", "optimal": "Optimal", "opt": "Optimal"}
    if normalized not in aliases:
        raise VirtualMemoryError("Algorithme memoire inconnu : %s" % algorithm)
    display_name = aliases[normalized]

    frames: List[Optional[int]] = [None] * frame_count
    fifo_order: Deque[int] = deque()
    last_used: Dict[int, int] = {}
    steps: List[ReplacementStep] = []
    faults = 0

    for index, page in enumerate(sequence):
        evicted: Optional[int] = None
        if page in frames:
            hit = True
            last_used[page] = index
        else:
            hit = False
            faults += 1
            if None in frames:
                frame_index = frames.index(None)
            elif display_name == "FIFO":
                frame_index = fifo_order.popleft()
            elif display_name == "LRU":
                frame_index = min(
                    range(frame_count), key=lambda item: (last_used[frames[item]], item)
                )
            else:  # Optimal : la page la plus lointaine (ou absente) est evacuee.
                def next_use(frame_index: int) -> float:
                    resident_page = frames[frame_index]
                    assert resident_page is not None
                    for future_index in range(index + 1, len(sequence)):
                        if sequence[future_index] == resident_page:
                            return float(future_index)
                    return float("inf")

                frame_index = max(range(frame_count), key=lambda item: (next_use(item), -item))

            evicted = frames[frame_index]
            if evicted is not None:
                last_used.pop(evicted, None)
            frames[frame_index] = page
            last_used[page] = index
            if display_name == "FIFO":
                fifo_order.append(frame_index)

        steps.append(ReplacementStep(index, page, tuple(frames), hit, evicted))

    return PageReplacementResult(
        algorithm=display_name,
        frame_count=frame_count,
        references=tuple(sequence),
        steps=tuple(steps),
        page_faults=faults,
    )


def parse_references(specification: str) -> List[int]:
    """Analyse une chaine comme ``7, 0, 1, 2``."""

    if not specification or not specification.strip():
        raise VirtualMemoryError("La chaine de references est vide.")
    try:
        values = [int(token.strip()) for token in specification.replace(";", ",").split(",")]
    except ValueError as error:
        raise VirtualMemoryError("Les references doivent etre separees par des virgules.") from error
    if any(token.strip() == "" for token in specification.replace(";", ",").split(",")):
        raise VirtualMemoryError("Une reference de page est manquante.")
    return values


def parse_page_table(specification: str) -> Dict[int, int]:
    """Analyse ``0:2,1:0`` en table page -> cadre."""

    if not specification or not specification.strip():
        raise VirtualMemoryError("La table de pages est vide.")
    page_table: Dict[int, int] = {}
    for item in specification.split(","):
        fields = [part.strip() for part in item.split(":")]
        if len(fields) != 2:
            raise VirtualMemoryError("Format de table attendu : page:cadre,page:cadre")
        try:
            page, frame = int(fields[0]), int(fields[1])
        except ValueError as error:
            raise VirtualMemoryError("Pages et cadres doivent etre des entiers.") from error
        if page < 0 or frame < 0:
            raise VirtualMemoryError("Pages et cadres doivent etre positifs ou nuls.")
        if page in page_table:
            raise VirtualMemoryError("Une page ne peut apparaitre qu'une seule fois.")
        page_table[page] = frame
    return page_table


class VirtualMemoryManager:
    """Traduit des adresses et maintient un TLB associatif a eviction LRU.

    La table de pages est prechargee pour isoler le mecanisme de traduction.
    Une page absente produit un defaut de page, sans que le gestionnaire ne
    choisisse un cadre : les politiques FIFO/LRU/Optimal sont simulees par la
    fonction dediee ``simulate_page_replacement``.
    """

    def __init__(
        self,
        page_size: int,
        page_table: Mapping[int, int],
        tlb_capacity: int = 4,
    ) -> None:
        if page_size <= 0:
            raise VirtualMemoryError("La taille de page doit etre strictement positive.")
        if tlb_capacity < 0:
            raise VirtualMemoryError("La capacite du TLB ne peut pas etre negative.")
        normalized_table: Dict[int, int] = {}
        for page, frame in page_table.items():
            if not isinstance(page, int) or not isinstance(frame, int) or page < 0 or frame < 0:
                raise VirtualMemoryError("La table contient une page ou un cadre invalide.")
            normalized_table[page] = frame
        self.page_size = page_size
        self.page_table = normalized_table
        self.tlb_capacity = tlb_capacity
        self._tlb: "OrderedDict[int, int]" = OrderedDict()
        self.tlb_hits = 0
        self.tlb_misses = 0

    @property
    def accesses(self) -> int:
        return self.tlb_hits + self.tlb_misses

    @property
    def tlb_hit_ratio(self) -> float:
        return self.tlb_hits / self.accesses if self.accesses else 0.0

    @property
    def tlb_entries(self) -> Tuple[Tuple[int, int], ...]:
        return tuple(self._tlb.items())

    def invalidate(self, page: int) -> None:
        """Invalide une entree TLB (a appeler apres eviction/remapping)."""

        self._tlb.pop(page, None)

    def map_page(self, page: int, frame: int) -> None:
        if page < 0 or frame < 0:
            raise VirtualMemoryError("Page et cadre doivent etre positifs ou nuls.")
        self.page_table[page] = frame
        self.invalidate(page)

    def unmap_page(self, page: int) -> None:
        self.page_table.pop(page, None)
        self.invalidate(page)

    def _cache_tlb(self, page: int, frame: int) -> None:
        if self.tlb_capacity == 0:
            return
        self._tlb.pop(page, None)
        while len(self._tlb) >= self.tlb_capacity:
            self._tlb.popitem(last=False)
        self._tlb[page] = frame

    def translate(self, logical_address: int) -> AddressTranslation:
        """Traduit une adresse logique et met a jour les statistiques TLB."""

        if not isinstance(logical_address, int) or logical_address < 0:
            raise VirtualMemoryError("L'adresse logique doit etre un entier positif ou nul.")
        page, offset = divmod(logical_address, self.page_size)
        if page in self._tlb:
            frame = self._tlb.pop(page)
            self._tlb[page] = frame  # la consultation rend l'entree la plus recente
            self.tlb_hits += 1
            return AddressTranslation(
                logical_address,
                page,
                offset,
                frame,
                frame * self.page_size + offset,
                True,
                False,
            )

        self.tlb_misses += 1
        if page not in self.page_table:
            return AddressTranslation(logical_address, page, offset, None, None, False, True)
        frame = self.page_table[page]
        self._cache_tlb(page, frame)
        return AddressTranslation(
            logical_address,
            page,
            offset,
            frame,
            frame * self.page_size + offset,
            False,
            False,
        )

    def effective_access_time(self, tlb_lookup_ns: float, memory_access_ns: float) -> float:
        """Calcule l'EAT sans cout de defaut de page.

        Hypothese : au hit, ``t_TLB + t_mem`` ; au miss, ``t_TLB + 2*t_mem``
        (consultation de la table puis acces a la donnee).
        """

        if not isfinite(tlb_lookup_ns) or not isfinite(memory_access_ns):
            raise VirtualMemoryError("Les temps d'acces doivent etre des nombres finis.")
        if tlb_lookup_ns < 0 or memory_access_ns < 0:
            raise VirtualMemoryError("Les temps d'acces ne peuvent pas etre negatifs.")
        hit_ratio = self.tlb_hit_ratio
        # Un acces memoire a la donnee est commun aux hits et aux misses.
        eat = tlb_lookup_ns + (2 - hit_ratio) * memory_access_ns
        if not isfinite(eat):
            raise VirtualMemoryError("Le temps d'acces effectif depasse la limite numerique.")
        return eat


def translate_address(
    logical_address: int,
    page_size: int,
    page_table: Mapping[int, int],
) -> AddressTranslation:
    """Raccourci pour une traduction sans TLB."""

    return VirtualMemoryManager(page_size, page_table, tlb_capacity=0).translate(logical_address)


def _format_table(headers: Sequence[str], rows: Sequence[Sequence[object]]) -> str:
    widths = [len(item) for item in headers]
    converted = [[str(value) for value in row] for row in rows]
    for row in converted:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(value))
    separator = "+".join("-" * (width + 2) for width in widths)
    lines = [
        " | ".join(value.ljust(widths[index]) for index, value in enumerate(headers)),
        separator,
    ]
    lines.extend(
        " | ".join(value.ljust(widths[index]) for index, value in enumerate(row))
        for row in converted
    )
    return "\n".join(lines)


def format_replacement(result: PageReplacementResult) -> str:
    """Affiche la trace pas a pas attendue durant la demonstration."""

    rows = []
    for step in result.steps:
        frames = " ".join("-" if page is None else str(page) for page in step.frames)
        rows.append(
            (
                step.index + 1,
                step.page,
                "hit" if step.hit else "defaut",
                "-" if step.evicted is None else step.evicted,
                frames,
            )
        )
    table = _format_table(["#", "Page", "Resultat", "Evincee", "Cadres"], rows)
    summary = (
        "%s : %d defauts, %d hits, taux de defaut %.2f%%"
        % (result.algorithm, result.page_faults, result.hits, result.fault_rate * 100)
    )
    return "%s\n%s" % (table, summary)


def format_translation(translation: AddressTranslation) -> str:
    if translation.page_fault:
        return (
            "Adresse logique %d -> page %d, deplacement %d : DEFAUT DE PAGE"
            % (translation.logical_address, translation.page, translation.offset)
        )
    source = "TLB hit" if translation.tlb_hit else "TLB miss / table des pages"
    return (
        "Adresse logique %d -> page %d, deplacement %d -> cadre %d -> adresse physique %d (%s)"
        % (
            translation.logical_address,
            translation.page,
            translation.offset,
            translation.frame,
            translation.physical_address,
            source,
        )
    )


def format_tlb(manager: VirtualMemoryManager) -> str:
    rows = [(page, frame) for page, frame in manager.tlb_entries]
    entries = _format_table(["Page", "Cadre"], rows) if rows else "(TLB vide)"
    return (
        "%s\nAcces TLB : %d, hits : %d, misses : %d, taux de hit : %.2f%%"
        % (entries, manager.accesses, manager.tlb_hits, manager.tlb_misses, manager.tlb_hit_ratio * 100)
    )
