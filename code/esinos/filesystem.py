"""Mini systeme de fichiers persistant pour le bonus ESINOS.

Ce module ne touche jamais au systeme de fichiers de l'hote, a l'exception
d'une image disque JSON fournie par l'appelant.  L'image contient une table
d'inodes fixe, un bitmap implicite (un bloc vaut ``None`` lorsqu'il est libre)
et les donnees de chaque bloc encodees en Base64.  Le Base64 permet de couper
un texte UTF-8 a n'importe quel octet sans corrompre les caracteres accentues.

Exemple minimal::

    fs = VirtualFileSystem("data/esinos.disk.json", create=True)
    fs.create("notes.txt", "Bonjour ESINOS")
    print(fs.read("notes.txt"))
    print(fs.inode_table())

La persistance est atomique : une image temporaire est ecrite puis renommee
seulement lorsque son contenu est complet.
"""

from __future__ import annotations

import base64
import binascii
import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union


__all__ = [
    "VirtualFileSystem",
    "MiniFileSystem",
    "FileSystem",
    "Inode",
    "FileSystemError",
    "DiskImageError",
    "DiskNotFormattedError",
    "DiskAlreadyExistsError",
    "InvalidFileNameError",
    "InvalidContentError",
    "FileAlreadyExistsError",
    "VirtualFileNotFoundError",
    "DiskFullError",
    "InodeTableFullError",
]


class FileSystemError(Exception):
    """Erreur de base du mini systeme de fichiers."""


class DiskImageError(FileSystemError):
    """L'image disque est absente, invalide ou incoherente."""


class DiskNotFormattedError(DiskImageError):
    """Aucune image disque formatee n'existe encore a cet emplacement."""


class DiskAlreadyExistsError(FileSystemError):
    """Une initialisation exclusive refuse d'ecraser une image existante."""


class InvalidFileNameError(FileSystemError):
    """Le nom de fichier ne respecte pas le format du simulateur."""


class InvalidContentError(FileSystemError):
    """Le contenu fourni ne peut pas etre stocke dans le disque simule."""


class FileAlreadyExistsError(FileSystemError):
    """Un fichier virtuel du meme nom existe deja."""


class VirtualFileNotFoundError(FileSystemError):
    """Le fichier virtuel demande n'existe pas."""


class DiskFullError(FileSystemError):
    """Le disque simule ne contient pas assez de blocs libres."""


class InodeTableFullError(FileSystemError):
    """La table d'inodes fixe est pleine."""


@dataclass(frozen=True)
class Inode:
    """Entree immutable de la table d'inodes."""

    inode_id: int
    name: str
    size: int
    blocks: Tuple[int, ...]

    def to_dict(self) -> Dict[str, Any]:
        """Retourne une representation JSON de l'inode."""

        return {
            "inode_id": self.inode_id,
            "name": self.name,
            "size": self.size,
            "blocks": list(self.blocks),
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "Inode":
        """Construit un inode sans masquer les erreurs de schema."""

        if not isinstance(raw, Mapping):
            raise DiskImageError("Une entree de la table d'inodes doit etre un objet JSON.")

        blocks = raw.get("blocks")
        if not isinstance(blocks, list):
            raise DiskImageError("Le champ 'blocks' d'un inode doit etre une liste.")

        return cls(
            inode_id=raw.get("inode_id"),
            name=raw.get("name"),
            size=raw.get("size"),
            blocks=tuple(blocks),
        )


class VirtualFileSystem:
    """Systeme de fichiers a allocation directe sur une image JSON.

    Les fichiers sont volontairement petits : chaque inode contient la liste
    de ses blocs directs.  Cela rend l'allocation, la liberation des blocs et
    la table d'inodes faciles a expliquer pendant la soutenance.

    Args:
        path: Chemin de l'image-disque JSON persistante.
        block_size: Taille d'un bloc en octets lors de la creation d'une image.
        block_count: Nombre total de blocs lors de la creation d'une image.
        inode_count: Taille fixe de la table d'inodes lors de la creation.
        create: Cree et formate une nouvelle image si elle est absente. Sans
            cette option, l'absence de disque leve ``DiskNotFormattedError``.
    """

    SCHEMA = "esinos-mini-filesystem"
    SCHEMA_VERSION = 1
    _NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")

    def __init__(
        self,
        path: Union[str, Path],
        *,
        block_count: int = 64,
        block_size: int = 64,
        inode_count: int = 16,
        create: bool = False,
    ) -> None:
        self.disk_path = Path(path)
        self._validate_configuration(block_size, block_count, inode_count)

        self.block_size = block_size
        self.block_count = block_count
        self.max_inodes = inode_count
        self._inodes: Dict[str, Inode] = {}
        self._blocks: List[Optional[str]] = []

        if self.disk_path.exists():
            self.reload()
        elif create:
            self.format()
        else:
            raise DiskNotFormattedError(
                "L'image disque n'existe pas. Utilisez create=True ou formattez-la : "
                + str(self.disk_path)
            )

    @classmethod
    def initialize_new(
        cls,
        path: Union[str, Path],
        *,
        block_count: int = 64,
        block_size: int = 64,
        inode_count: int = 16,
    ) -> "VirtualFileSystem":
        """Cree une nouvelle image uniquement si aucun chemin ne l'occupe.

        Cette methode est destinee a ``esinos fs init``. Contrairement a
        ``VirtualFileSystem(..., create=True)``, elle ne charge ni ne reformate
        une image existante. Le lien physique ``os.link`` publie le fichier
        temporaire de facon atomique et echoue si un autre processus vient de
        creer la meme image entre-temps.
        """

        cls._validate_configuration(block_size, block_count, inode_count)
        filesystem = cls.__new__(cls)
        filesystem.disk_path = Path(path)
        filesystem.block_size = block_size
        filesystem.block_count = block_count
        filesystem.max_inodes = inode_count
        filesystem._inodes = {}
        filesystem._blocks = [None] * block_count

        payload = filesystem._serialize_state(filesystem._inodes, filesystem._blocks)
        filesystem._exclusive_create(payload)
        return filesystem

    # ------------------------------------------------------------------
    # API publique : operations de fichiers
    # ------------------------------------------------------------------
    def format(self) -> None:
        """Reinitialise le disque, tous les inodes et tous les blocs.

        Cette operation est destructive pour l'image virtuelle uniquement.
        """

        self._replace_state({}, [None] * self.block_count)

    format_disk = format

    def create(self, name: str, content: str = "") -> Inode:
        """Cree un fichier avec son contenu initial et retourne son inode."""

        self._validate_name(name)
        self._validate_content(content)
        if name in self._inodes:
            raise FileAlreadyExistsError("Le fichier existe deja : " + name)
        if len(self._inodes) >= self.max_inodes:
            raise InodeTableFullError("La table d'inodes est pleine.")

        inode_id = self._next_free_inode_id()
        inodes = dict(self._inodes)
        blocks = list(self._blocks)
        inode = self._store_content(
            inode_id=inode_id,
            name=name,
            content=content,
            old_blocks=(),
            blocks=blocks,
        )
        inodes[name] = inode
        self._replace_state(inodes, blocks)
        return inode

    create_file = create

    def read(self, name: str) -> str:
        """Lit et retourne le contenu UTF-8 d'un fichier virtuel."""

        inode = self.get_inode(name)
        return self._read_inode_content(inode, self._blocks)

    read_file = read

    def write(self, name: str, content: str, *, append: bool = False) -> Inode:
        """Remplace le contenu d'un fichier ou y ajoute ``content``.

        La reecriture libere d'abord les anciens blocs dans une copie de
        travail. Ainsi, le fichier peut reutiliser ses propres blocs meme si
        le disque ne possede aucun autre bloc libre.
        """

        self._validate_name(name)
        self._validate_content(content)
        if not isinstance(append, bool):
            raise InvalidContentError("L'option append doit valoir True ou False.")

        previous = self._inodes.get(name)
        if previous is None:
            raise VirtualFileNotFoundError("Fichier introuvable : " + name)

        if append:
            content = self._read_inode_content(previous, self._blocks) + content

        inodes = dict(self._inodes)
        blocks = list(self._blocks)
        replacement = self._store_content(
            inode_id=previous.inode_id,
            name=name,
            content=content,
            old_blocks=previous.blocks,
            blocks=blocks,
        )
        inodes[name] = replacement
        self._replace_state(inodes, blocks)
        return replacement

    write_file = write

    def delete(self, name: str) -> None:
        """Supprime un fichier et libere tous ses blocs alloues."""

        inode = self.get_inode(name)
        inodes = dict(self._inodes)
        blocks = list(self._blocks)

        for block_index in inode.blocks:
            blocks[block_index] = None
        del inodes[name]
        self._replace_state(inodes, blocks)

    delete_file = delete

    def exists(self, name: str) -> bool:
        """Indique si ``name`` est present dans le repertoire racine."""

        self._validate_name(name)
        return name in self._inodes

    def get_inode(self, name: str) -> Inode:
        """Retourne l'inode immutable d'un fichier, ou leve une erreur."""

        self._validate_name(name)
        inode = self._inodes.get(name)
        if inode is None:
            raise VirtualFileNotFoundError("Fichier introuvable : " + name)
        return inode

    def list_files(self) -> List[Inode]:
        """Liste les fichiers par numero d'inode, pour un affichage stable."""

        return sorted(self._inodes.values(), key=lambda inode: inode.inode_id)

    ls = list_files

    def inode_table(self) -> List[Dict[str, Any]]:
        """Retourne les entrees occupees et libres de la table d'inodes.

        Chaque ligne fournit ``inode_id``, ``allocated``, ``name``, ``size``
        et ``blocks``. Les entrees libres sont conservees pour rendre visible
        le principe de la table d'inodes fixe lors de la demonstration.
        """

        by_id = {inode.inode_id: inode for inode in self._inodes.values()}
        rows: List[Dict[str, Any]] = []
        for inode_id in range(1, self.max_inodes + 1):
            inode = by_id.get(inode_id)
            rows.append(
                {
                    "inode_id": inode_id,
                    "allocated": inode is not None,
                    "name": inode.name if inode else None,
                    "size": inode.size if inode else 0,
                    "blocks": list(inode.blocks) if inode else [],
                }
            )
        return rows

    table_inodes = inode_table

    def status(self) -> Dict[str, Any]:
        """Retourne des compteurs utiles au menu de demonstration."""

        used_blocks = sum(block is not None for block in self._blocks)
        return {
            "disk_path": str(self.disk_path),
            "block_size": self.block_size,
            "block_count": self.block_count,
            "used_blocks": used_blocks,
            "free_blocks": self.block_count - used_blocks,
            "max_inodes": self.max_inodes,
            "used_inodes": len(self._inodes),
            "free_inodes": self.max_inodes - len(self._inodes),
        }

    # ------------------------------------------------------------------
    # Persistance et validation
    # ------------------------------------------------------------------
    def reload(self) -> None:
        """Recharge et valide l'image disque depuis le disque hote."""

        try:
            with self.disk_path.open("r", encoding="utf-8") as stream:
                raw = json.load(stream)
        except FileNotFoundError as exc:
            raise DiskImageError("Image disque introuvable : " + str(self.disk_path)) from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise DiskImageError("Impossible de lire l'image disque : " + str(exc)) from exc

        if not isinstance(raw, Mapping):
            raise DiskImageError("L'image disque doit contenir un objet JSON.")
        if raw.get("schema") != self.SCHEMA:
            raise DiskImageError("Format d'image disque ESINOS non reconnu.")
        if raw.get("version") != self.SCHEMA_VERSION:
            raise DiskImageError("Version d'image disque non prise en charge.")

        block_size = raw.get("block_size")
        block_count = raw.get("block_count")
        max_inodes = raw.get("max_inodes")
        self._validate_configuration(block_size, block_count, max_inodes)

        raw_blocks = raw.get("blocks")
        raw_inodes = raw.get("inodes")
        if not isinstance(raw_blocks, list):
            raise DiskImageError("Le champ 'blocks' doit etre une liste.")
        if not isinstance(raw_inodes, list):
            raise DiskImageError("Le champ 'inodes' doit etre une liste.")

        inodes: Dict[str, Inode] = {}
        for raw_inode in raw_inodes:
            inode = Inode.from_dict(raw_inode)
            if inode.name in inodes:
                raise DiskImageError("Deux inodes portent le meme nom : " + str(inode.name))
            inodes[inode.name] = inode

        blocks: List[Optional[str]] = list(raw_blocks)
        self._validate_state(
            inodes,
            blocks,
            block_size=block_size,
            block_count=block_count,
            max_inodes=max_inodes,
        )

        self.block_size = block_size
        self.block_count = block_count
        self.max_inodes = max_inodes
        self._inodes = inodes
        self._blocks = blocks

    def _replace_state(
        self, inodes: Dict[str, Inode], blocks: List[Optional[str]]
    ) -> None:
        """Valide, ecrit atomiquement puis rend un nouvel etat actif."""

        self._validate_state(
            inodes,
            blocks,
            block_size=self.block_size,
            block_count=self.block_count,
            max_inodes=self.max_inodes,
        )
        payload = self._serialize_state(inodes, blocks)
        self._atomic_write(payload)
        self._inodes = inodes
        self._blocks = blocks

    def _serialize_state(
        self, inodes: Dict[str, Inode], blocks: Sequence[Optional[str]]
    ) -> Dict[str, Any]:
        return {
            "schema": self.SCHEMA,
            "version": self.SCHEMA_VERSION,
            "block_size": self.block_size,
            "block_count": self.block_count,
            "max_inodes": self.max_inodes,
            "inodes": [inode.to_dict() for inode in self.list_from(inodes)],
            "blocks": list(blocks),
        }

    @staticmethod
    def list_from(inodes: Mapping[str, Inode]) -> List[Inode]:
        """Trie une collection d'inodes sans dependre de l'etat courant."""

        return sorted(inodes.values(), key=lambda inode: inode.inode_id)

    def _atomic_write(self, payload: Mapping[str, Any]) -> None:
        """Ecrit l'image dans un fichier temporaire puis la remplace."""

        temporary_path = self._write_temporary_json(payload)
        try:
            os.replace(str(temporary_path), str(self.disk_path))
            self._sync_directory(self.disk_path.parent)
        except OSError as exc:
            raise DiskImageError("Impossible d'ecrire l'image disque : " + str(exc)) from exc
        finally:
            # os.replace supprime normalement le temporaire. Ce garde-fou
            # couvre les erreurs survenues avant le renommage.
            self._cleanup_temporary(temporary_path)

    def _exclusive_create(self, payload: Mapping[str, Any]) -> None:
        """Publie une image neuve sans jamais ecraser une destination.

        Le fichier temporaire et la destination sont dans le meme repertoire.
        ``link`` cree donc un nouveau nom pour le fichier entier, de maniere
        atomique. Si la destination existe deja, meme si son JSON est corrompu,
        le noyau refuse le lien et aucun octet de cette destination ne change.
        """

        temporary_path = self._write_temporary_json(payload)
        try:
            try:
                os.link(str(temporary_path), str(self.disk_path))
            except FileExistsError as exc:
                raise DiskAlreadyExistsError(
                    "Refus d'ecraser une image disque existante : " + str(self.disk_path)
                ) from exc
            except OSError as exc:
                raise DiskImageError(
                    "Impossible de publier l'image disque sans ecrasement : " + str(exc)
                ) from exc
            self._sync_directory(self.disk_path.parent)
        finally:
            self._cleanup_temporary(temporary_path)

    def _write_temporary_json(self, payload: Mapping[str, Any]) -> Path:
        """Ecrit et synchronise une image temporaire dans le bon repertoire."""

        parent = self.disk_path.parent
        try:
            parent.mkdir(parents=True, exist_ok=True)
            descriptor, temporary_name = tempfile.mkstemp(
                prefix="." + self.disk_path.name + ".",
                suffix=".tmp",
                dir=str(parent),
                text=True,
            )
        except OSError as exc:
            raise DiskImageError("Impossible de preparer l'image disque : " + str(exc)) from exc

        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(payload, stream, ensure_ascii=False, indent=2, sort_keys=True)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
        except OSError as exc:
            self._cleanup_temporary(temporary_path)
            raise DiskImageError("Impossible d'ecrire l'image disque : " + str(exc)) from exc
        return temporary_path

    @staticmethod
    def _cleanup_temporary(temporary_path: Path) -> None:
        """Supprime sans bruit un temporaire deja publie ou abandonne."""

        try:
            temporary_path.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            pass

    @staticmethod
    def _sync_directory(directory: Path) -> None:
        """Tente de rendre le renommage durable sans echouer sur une plate-forme.

        Certains systemes ne permettent pas ``fsync`` sur un descripteur de
        repertoire ; l'ecriture de l'image reste tout de meme valide dans ce
        cas, d'ou l'ignorance ciblee de cette erreur optionnelle.
        """

        try:
            descriptor = os.open(str(directory), os.O_RDONLY)
        except OSError:
            return
        try:
            os.fsync(descriptor)
        except OSError:
            pass
        finally:
            os.close(descriptor)

    # ------------------------------------------------------------------
    # Allocation interne
    # ------------------------------------------------------------------
    def _store_content(
        self,
        *,
        inode_id: int,
        name: str,
        content: str,
        old_blocks: Sequence[int],
        blocks: List[Optional[str]],
    ) -> Inode:
        """Alloue de nouveaux blocs dans ``blocks`` et fabrique un inode."""

        encoded_chunks = self._encode_content(content)
        for block_index in old_blocks:
            blocks[block_index] = None

        free_blocks = [index for index, value in enumerate(blocks) if value is None]
        if len(encoded_chunks) > len(free_blocks):
            raise DiskFullError(
                "Espace insuffisant : "
                + str(len(encoded_chunks))
                + " blocs requis, "
                + str(len(free_blocks))
                + " disponibles."
            )

        allocated = tuple(free_blocks[: len(encoded_chunks)])
        for block_index, chunk in zip(allocated, encoded_chunks):
            blocks[block_index] = chunk

        return Inode(
            inode_id=inode_id,
            name=name,
            size=len(content.encode("utf-8")),
            blocks=allocated,
        )

    def _encode_content(self, content: str) -> List[str]:
        raw = content.encode("utf-8")
        return [
            base64.b64encode(raw[offset : offset + self.block_size]).decode("ascii")
            for offset in range(0, len(raw), self.block_size)
        ]

    def _read_inode_content(self, inode: Inode, blocks: Sequence[Optional[str]]) -> str:
        chunks: List[bytes] = []
        for block_index in inode.blocks:
            encoded = blocks[block_index]
            if encoded is None:
                raise DiskImageError(
                    "L'inode " + str(inode.inode_id) + " reference un bloc libre."
                )
            chunks.append(self._decode_block(encoded))
        raw = b"".join(chunks)
        if len(raw) != inode.size:
            raise DiskImageError(
                "La taille stockee pour le fichier " + inode.name + " est incoherente."
            )
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise DiskImageError(
                "Le contenu du fichier " + inode.name + " n'est pas du texte UTF-8 valide."
            ) from exc

    def _next_free_inode_id(self) -> int:
        used = {inode.inode_id for inode in self._inodes.values()}
        for inode_id in range(1, self.max_inodes + 1):
            if inode_id not in used:
                return inode_id
        raise InodeTableFullError("La table d'inodes est pleine.")

    # ------------------------------------------------------------------
    # Validation defensive de l'image et des donnees saisies
    # ------------------------------------------------------------------
    @classmethod
    def _validate_name(cls, name: Any) -> None:
        if not isinstance(name, str) or not cls._NAME_RE.fullmatch(name):
            raise InvalidFileNameError(
                "Nom invalide. Utilisez 1 a 64 caracteres : lettres, chiffres, '.', '_' ou '-'."
            )
        if name in {".", ".."}:
            raise InvalidFileNameError("Les noms '.' et '..' sont reserves.")

    @staticmethod
    def _validate_content(content: Any) -> None:
        if not isinstance(content, str):
            raise InvalidContentError("Le contenu d'un fichier doit etre une chaine de caracteres.")

    @staticmethod
    def _validate_configuration(block_size: Any, block_count: Any, max_inodes: Any) -> None:
        values = {
            "block_size": block_size,
            "block_count": block_count,
            "max_inodes": max_inodes,
        }
        for label, value in values.items():
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise DiskImageError(label + " doit etre un entier strictement positif.")
            # Une borne elevee mais finie evite de tenter de charger une image
            # malveillante qui demanderait une quantite enorme de memoire.
            if value > 1_000_000:
                raise DiskImageError(label + " depasse la limite autorisee.")

    @classmethod
    def _decode_block(cls, encoded: Any) -> bytes:
        if not isinstance(encoded, str) or not encoded:
            raise DiskImageError("Un bloc alloue doit contenir une chaine Base64 non vide.")
        try:
            return base64.b64decode(encoded.encode("ascii"), validate=True)
        except (UnicodeEncodeError, ValueError, binascii.Error) as exc:
            raise DiskImageError("Un bloc contient des donnees Base64 invalides.") from exc

    @classmethod
    def _validate_state(
        cls,
        inodes: Mapping[str, Inode],
        blocks: Sequence[Optional[str]],
        *,
        block_size: int,
        block_count: int,
        max_inodes: int,
    ) -> None:
        """Verifie toutes les invariantes avant une ecriture ou un chargement."""

        cls._validate_configuration(block_size, block_count, max_inodes)
        if len(blocks) != block_count:
            raise DiskImageError("Le nombre de blocs de l'image est incoherent.")
        if len(inodes) > max_inodes:
            raise DiskImageError("La table d'inodes depasse sa capacite.")

        allocated_blocks = set()
        inode_ids = set()
        for mapping_name, inode in inodes.items():
            if not isinstance(inode, Inode):
                raise DiskImageError("La table contient un inode invalide.")
            cls._validate_name(mapping_name)
            cls._validate_name(inode.name)
            if mapping_name != inode.name:
                raise DiskImageError("La cle d'un inode ne correspond pas a son nom.")
            if (
                isinstance(inode.inode_id, bool)
                or not isinstance(inode.inode_id, int)
                or not 1 <= inode.inode_id <= max_inodes
            ):
                raise DiskImageError("Numero d'inode invalide.")
            if inode.inode_id in inode_ids:
                raise DiskImageError("Deux entrees utilisent le meme numero d'inode.")
            inode_ids.add(inode.inode_id)

            if isinstance(inode.size, bool) or not isinstance(inode.size, int) or inode.size < 0:
                raise DiskImageError("Taille d'inode invalide.")
            if not isinstance(inode.blocks, tuple):
                raise DiskImageError("Les blocs d'un inode doivent etre immuables.")

            required_blocks = (inode.size + block_size - 1) // block_size
            if len(inode.blocks) != required_blocks:
                raise DiskImageError(
                    "Le nombre de blocs de l'inode " + str(inode.inode_id) + " est incoherent."
                )

            content_chunks: List[bytes] = []
            for position, block_index in enumerate(inode.blocks):
                if isinstance(block_index, bool) or not isinstance(block_index, int):
                    raise DiskImageError("Indice de bloc invalide.")
                if not 0 <= block_index < block_count:
                    raise DiskImageError("Indice de bloc hors limites.")
                if block_index in allocated_blocks:
                    raise DiskImageError("Un bloc est reference par plusieurs inodes.")
                allocated_blocks.add(block_index)

                encoded = blocks[block_index]
                if encoded is None:
                    raise DiskImageError("Un inode reference un bloc libre.")
                chunk = cls._decode_block(encoded)
                if not 0 < len(chunk) <= block_size:
                    raise DiskImageError("La taille d'un bloc alloue est invalide.")
                if position < len(inode.blocks) - 1 and len(chunk) != block_size:
                    raise DiskImageError("Seul le dernier bloc d'un fichier peut etre partiel.")
                content_chunks.append(chunk)

            content = b"".join(content_chunks)
            if len(content) != inode.size:
                raise DiskImageError("La taille d'un inode ne correspond pas a ses blocs.")
            try:
                content.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise DiskImageError("Un fichier stocke n'est pas du texte UTF-8 valide.") from exc

        for block_index, encoded in enumerate(blocks):
            if encoded is None:
                continue
            if block_index not in allocated_blocks:
                raise DiskImageError("Un bloc alloue n'est reference par aucun inode.")
            chunk = cls._decode_block(encoded)
            if not 0 < len(chunk) <= block_size:
                raise DiskImageError("La taille d'un bloc alloue est invalide.")


# Alias court, pratique pour un import depuis le menu integre.
MiniFileSystem = VirtualFileSystem
FileSystem = VirtualFileSystem
