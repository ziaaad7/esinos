"""Algorithmes d'ordonnancement du CPU utilises par ESINOS.

Les temps sont entiers et representent des unites de temps abstraites.  Les
priorites les plus petites sont les plus elevees, convention explicitee dans
l'interface et le README.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque, Iterable, List, Optional, Sequence, Tuple


class SchedulerError(ValueError):
    """Erreur de validation des donnees d'ordonnancement."""


@dataclass(frozen=True)
class Process:
    """Description immuable d'un processus a planifier."""

    pid: str
    arrival: int
    burst: int
    priority: int = 0

    def __post_init__(self) -> None:
        if not self.pid or not self.pid.strip():
            raise SchedulerError("Chaque processus doit avoir un PID non vide.")
        if self.pid.upper() == "IDLE":
            raise SchedulerError("Le PID 'IDLE' est reserve au diagramme de Gantt.")
        if self.arrival < 0:
            raise SchedulerError("Le temps d'arrivee ne peut pas etre negatif.")
        if self.burst <= 0:
            raise SchedulerError("Le temps CPU (burst) doit etre strictement positif.")


@dataclass(frozen=True)
class GanttSlice:
    """Une tranche d'execution (ou d'inactivite) dans le diagramme de Gantt."""

    label: str
    start: int
    end: int

    def __post_init__(self) -> None:
        if self.end <= self.start:
            raise SchedulerError("Une tranche Gantt doit avoir une duree positive.")


@dataclass(frozen=True)
class ProcessMetrics:
    """Mesures de fin, de sejour et d'attente d'un processus termine."""

    pid: str
    arrival: int
    burst: int
    priority: int
    completion: int
    waiting: int
    turnaround: int


@dataclass(frozen=True)
class ScheduleResult:
    """Resultat complet et affichable d'une simulation d'ordonnancement."""

    algorithm: str
    timeline: Tuple[GanttSlice, ...]
    metrics: Tuple[ProcessMetrics, ...]
    quantum: Optional[int] = None

    @property
    def average_waiting(self) -> float:
        return sum(item.waiting for item in self.metrics) / len(self.metrics)

    @property
    def average_turnaround(self) -> float:
        return sum(item.turnaround for item in self.metrics) / len(self.metrics)


def _validate_processes(processes: Iterable[Process]) -> List[Process]:
    process_list = list(processes)
    if not process_list:
        raise SchedulerError("Il faut au moins un processus a planifier.")
    seen = set()
    for process in process_list:
        if not isinstance(process, Process):
            raise SchedulerError("Les entrees doivent etre des objets Process.")
        if process.pid in seen:
            raise SchedulerError("Les PID doivent etre uniques.")
        seen.add(process.pid)
    return process_list


def _record_slice(timeline: List[GanttSlice], label: str, start: int, end: int) -> None:
    """Ajoute une tranche et fusionne les tranches consecutives identiques."""

    if end <= start:
        return
    if timeline and timeline[-1].label == label and timeline[-1].end == start:
        previous = timeline[-1]
        timeline[-1] = GanttSlice(label, previous.start, end)
    else:
        timeline.append(GanttSlice(label, start, end))


def _build_result(
    algorithm: str,
    processes: Sequence[Process],
    timeline: List[GanttSlice],
    completion: dict[str, int],
    quantum: Optional[int] = None,
) -> ScheduleResult:
    metrics: List[ProcessMetrics] = []
    for process in processes:
        end = completion[process.pid]
        turnaround = end - process.arrival
        waiting = turnaround - process.burst
        metrics.append(
            ProcessMetrics(
                pid=process.pid,
                arrival=process.arrival,
                burst=process.burst,
                priority=process.priority,
                completion=end,
                waiting=waiting,
                turnaround=turnaround,
            )
        )
    return ScheduleResult(algorithm, tuple(timeline), tuple(metrics), quantum)


def _run_non_preemptive(processes: Sequence[Process], algorithm: str) -> ScheduleResult:
    """Execute FCFS, SJF non preemptif ou Priority non preemptif."""

    pending = list(processes)
    timeline: List[GanttSlice] = []
    completion: dict[str, int] = {}
    clock = 0

    while pending:
        ready = [process for process in pending if process.arrival <= clock]
        if not ready:
            next_arrival = min(process.arrival for process in pending)
            _record_slice(timeline, "IDLE", clock, next_arrival)
            clock = next_arrival
            continue

        if algorithm == "fcfs":
            selected = min(ready, key=lambda item: (item.arrival, item.pid))
            display_name = "FCFS"
        elif algorithm == "sjf":
            selected = min(ready, key=lambda item: (item.burst, item.arrival, item.pid))
            display_name = "SJF (non preemptif)"
        else:
            selected = min(ready, key=lambda item: (item.priority, item.arrival, item.pid))
            display_name = "Priority (non preemptif)"

        end = clock + selected.burst
        _record_slice(timeline, selected.pid, clock, end)
        clock = end
        completion[selected.pid] = clock
        pending.remove(selected)

    return _build_result(display_name, processes, timeline, completion)


def _run_round_robin(processes: Sequence[Process], quantum: int) -> ScheduleResult:
    if quantum <= 0:
        raise SchedulerError("Le quantum Round Robin doit etre strictement positif.")

    future = sorted(processes, key=lambda item: (item.arrival, item.pid))
    remaining = {process.pid: process.burst for process in processes}
    ready: Deque[Process] = deque()
    timeline: List[GanttSlice] = []
    completion: dict[str, int] = {}
    index = 0
    clock = 0

    while index < len(future) or ready:
        if not ready:
            next_arrival = future[index].arrival
            _record_slice(timeline, "IDLE", clock, next_arrival)
            clock = max(clock, next_arrival)
            while index < len(future) and future[index].arrival <= clock:
                ready.append(future[index])
                index += 1

        current = ready.popleft()
        duration = min(quantum, remaining[current.pid])
        end = clock + duration
        _record_slice(timeline, current.pid, clock, end)
        clock = end
        remaining[current.pid] -= duration

        # Les arrivees a la fin de la tranche sont placees avant la re-insertion
        # du processus interrompu : c'est la convention documentee pour ESINOS.
        while index < len(future) and future[index].arrival <= clock:
            ready.append(future[index])
            index += 1

        if remaining[current.pid] > 0:
            ready.append(current)
        else:
            completion[current.pid] = clock

    return _build_result("Round Robin", processes, timeline, completion, quantum)


def run_scheduler(
    processes: Iterable[Process], algorithm: str, quantum: Optional[int] = None
) -> ScheduleResult:
    """Simule un ordonnanceur et retourne le Gantt et les metriques.

    ``algorithm`` accepte ``fcfs``, ``sjf``, ``rr`` et ``priority``. SJF et
    Priority sont non preemptifs ; Round Robin reste preemptif par quantum.
    """

    process_list = _validate_processes(processes)
    normalized = algorithm.lower().strip().replace("_", "-")
    if normalized == "fcfs":
        return _run_non_preemptive(process_list, "fcfs")
    if normalized == "sjf":
        return _run_non_preemptive(process_list, "sjf")
    if normalized in {"priority", "priorite"}:
        return _run_non_preemptive(process_list, "priority")
    if normalized in {"rr", "round-robin", "roundrobin"}:
        if quantum is None:
            raise SchedulerError("Round Robin exige un quantum.")
        return _run_round_robin(process_list, quantum)
    raise SchedulerError("Algorithme inconnu : %s" % algorithm)


def parse_processes(specification: str) -> List[Process]:
    """Analyse ``P1:0:5:2,P2:1:3:1`` en une liste de processus.

    Le quatrieme champ (priorite) est facultatif et vaut 0 par defaut.
    """

    if not specification or not specification.strip():
        raise SchedulerError("La liste de processus est vide.")
    parsed: List[Process] = []
    for raw_process in specification.split(","):
        fields = [field.strip() for field in raw_process.split(":")]
        if len(fields) not in {3, 4}:
            raise SchedulerError(
                "Format attendu : PID:arrivee:burst[:priorite], separes par des virgules."
            )
        try:
            arrival = int(fields[1])
            burst = int(fields[2])
            priority = int(fields[3]) if len(fields) == 4 else 0
        except ValueError as error:
            raise SchedulerError("Les temps et la priorite doivent etre des entiers.") from error
        parsed.append(Process(fields[0], arrival, burst, priority))
    return parsed


def format_gantt(timeline: Sequence[GanttSlice]) -> str:
    """Retourne une representation textuelle compacte et lisible du Gantt."""

    return " -> ".join(
        "%s [%d-%d]" % (slice_.label, slice_.start, slice_.end)
        for slice_ in timeline
    )


def _format_table(headers: Sequence[str], rows: Sequence[Sequence[object]]) -> str:
    widths = [len(header) for header in headers]
    rendered_rows = [[str(value) for value in row] for row in rows]
    for row in rendered_rows:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(value))
    separator = "+".join("-" * (width + 2) for width in widths)
    lines = [
        " | ".join(header.ljust(widths[index]) for index, header in enumerate(headers)),
        separator,
    ]
    for row in rendered_rows:
        lines.append(" | ".join(value.ljust(widths[index]) for index, value in enumerate(row)))
    return "\n".join(lines)


def format_schedule(result: ScheduleResult) -> str:
    """Formate un resultat pour l'interface interactive ou la demonstration."""

    title = "Ordonnanceur : %s" % result.algorithm
    if result.quantum is not None:
        title += " (quantum = %d)" % result.quantum
    rows = [
        (
            item.pid,
            item.arrival,
            item.burst,
            item.priority,
            item.completion,
            item.waiting,
            item.turnaround,
        )
        for item in result.metrics
    ]
    table = _format_table(
        ["PID", "AT", "BT", "Prio", "Fin (CT)", "Attente", "Sejour"],
        rows,
    )
    averages = "Moyennes : attente = %.2f, sejour = %.2f" % (
        result.average_waiting,
        result.average_turnaround,
    )
    return "%s\nGantt : %s\n\n%s\n%s" % (title, format_gantt(result.timeline), table, averages)
