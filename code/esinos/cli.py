"""Interface terminal et demonstration reproductible d'ESINOS."""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path
from typing import List, Optional, Sequence

from .filesystem import DiskNotFormattedError, FileSystemError, VirtualFileSystem
from .memory import (
    VirtualMemoryError,
    VirtualMemoryManager,
    format_replacement,
    format_tlb,
    format_translation,
    parse_page_table,
    parse_references,
    simulate_page_replacement,
)
from .scheduler import (
    Process,
    SchedulerError,
    format_schedule,
    parse_processes,
    run_scheduler,
)


SAMPLE_PROCESSES = [
    Process("P1", arrival=0, burst=7, priority=2),
    Process("P2", arrival=2, burst=4, priority=1),
    Process("P3", arrival=4, burst=1, priority=3),
    Process("P4", arrival=5, burst=4, priority=2),
]
SAMPLE_REFERENCES = [7, 0, 1, 2, 0, 3, 0, 4, 2, 3, 0, 3, 2]
SAMPLE_PAGE_TABLE = {0: 5, 1: 2, 2: 7, 3: 1}
# 70 et 75 partagent la page 1. L'adresse 260 montre le defaut sur la page 4.
SAMPLE_ADDRESSES = (5, 70, 75, 130, 5, 195, 70, 260)


def _format_table(headers: Sequence[str], rows: Sequence[Sequence[object]]) -> str:
    widths = [len(header) for header in headers]
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


def _banner(title: str) -> None:
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def _ask(prompt: str, default: Optional[str] = None) -> str:
    suffix = " [%s]" % default if default is not None else ""
    try:
        answer = input(prompt + suffix + " : ").strip()
    except EOFError:
        raise KeyboardInterrupt()
    return answer if answer else (default or "")


def _ask_int(prompt: str, default: int, minimum: int = 0) -> int:
    while True:
        raw = _ask(prompt, str(default))
        try:
            value = int(raw)
        except ValueError:
            print("Veuillez saisir un entier.")
            continue
        if value < minimum:
            print("La valeur doit etre superieure ou egale a %d." % minimum)
            continue
        return value


def _ask_yes_no(prompt: str, default: bool = False) -> bool:
    default_label = "o" if default else "n"
    while True:
        answer = _ask(prompt + " (o/n)", default_label).lower()
        if answer in {"o", "oui", "y", "yes"}:
            return True
        if answer in {"n", "non", "no"}:
            return False
        print("Repondez par o ou n.")


def _sample_process_spec() -> str:
    return ",".join(
        "%s:%d:%d:%d" % (process.pid, process.arrival, process.burst, process.priority)
        for process in SAMPLE_PROCESSES
    )


def _display_scheduler(processes: Sequence[Process], algorithm: str, quantum: Optional[int]) -> None:
    result = run_scheduler(processes, algorithm, quantum)
    print(format_schedule(result))


def _interactive_scheduler() -> None:
    _banner("ORDONNANCEUR CPU")
    print("Format des processus : PID:arrivee:burst:priorite")
    specification = _ask("Liste (priorite faible = plus urgente)", _sample_process_spec())
    try:
        processes = parse_processes(specification)
    except SchedulerError as error:
        print("Erreur : %s" % error)
        return

    print("1) FCFS  2) SJF  3) Round Robin  4) Priority")
    choices = {
        "1": "fcfs",
        "2": "sjf",
        "3": "rr",
        "4": "priority",
    }
    selection = _ask("Algorithme", "3")
    algorithm = choices.get(selection)
    if algorithm is None:
        print("Choix d'algorithme inconnu.")
        return
    quantum = _ask_int("Quantum", 2, 1) if algorithm == "rr" else None
    try:
        _display_scheduler(processes, algorithm, quantum)
    except SchedulerError as error:
        print("Erreur : %s" % error)


def _interactive_replacement() -> None:
    _banner("REMPLACEMENT DE PAGES")
    default_refs = ",".join(str(page) for page in SAMPLE_REFERENCES)
    raw_references = _ask("References de pages", default_refs)
    frames = _ask_int("Nombre de cadres", 3, 1)
    print("1) FIFO  2) LRU  3) Optimal")
    algorithm = {"1": "fifo", "2": "lru", "3": "optimal"}.get(_ask("Algorithme", "1"))
    if algorithm is None:
        print("Choix d'algorithme inconnu.")
        return
    try:
        result = simulate_page_replacement(parse_references(raw_references), frames, algorithm)
        print(format_replacement(result))
    except VirtualMemoryError as error:
        print("Erreur : %s" % error)


def _interactive_translation() -> None:
    _banner("TRADUCTION LOGIQUE -> PHYSIQUE, TLB ET EAT")
    default_table = ",".join("%d:%d" % item for item in SAMPLE_PAGE_TABLE.items())
    try:
        page_size = _ask_int("Taille de page (octets)", 64, 1)
        capacity = _ask_int("Capacite TLB", 2, 0)
        table = parse_page_table(_ask("Table page:cadre", default_table))
        manager = VirtualMemoryManager(page_size, table, capacity)
        default_addresses = ", ".join(map(str, SAMPLE_ADDRESSES))
        addresses = parse_references(_ask("Adresses logiques", default_addresses))
        for address in addresses:
            print(format_translation(manager.translate(address)))
        print("\n" + format_tlb(manager))
        tlb_time = float(_ask("Temps TLB (ns)", "10"))
        memory_time = float(_ask("Temps memoire (ns)", "100"))
        print("EAT (sans cout de defaut de page) : %.2f ns" % manager.effective_access_time(tlb_time, memory_time))
    except (ValueError, VirtualMemoryError) as error:
        print("Erreur : %s" % error)


def _default_disk_path() -> Path:
    return Path(__file__).resolve().parent.parent / "data" / "esinos.disk.json"


def _print_files(fs: VirtualFileSystem) -> None:
    files = fs.list_files()
    if not files:
        print("Aucun fichier dans le disque virtuel.")
        return
    print(
        _format_table(
            ["Inode", "Nom", "Taille (octets)", "Blocs"],
            [(inode.inode_id, inode.name, inode.size, ",".join(map(str, inode.blocks)) or "-") for inode in files],
        )
    )


def _print_inodes(fs: VirtualFileSystem) -> None:
    rows = [
        (
            row["inode_id"],
            "occupe" if row["allocated"] else "libre",
            row["name"] or "-",
            row["size"],
            ",".join(map(str, row["blocks"])) or "-",
        )
        for row in fs.inode_table()
    ]
    print(_format_table(["Inode", "Etat", "Nom", "Taille", "Blocs directs"], rows))


def _open_interactive_disk(path: Path) -> Optional[VirtualFileSystem]:
    try:
        return VirtualFileSystem(path)
    except DiskNotFormattedError:
        print("Aucun disque virtuel initialise a %s." % path)
        if _ask_yes_no("Le creer maintenant ?", True):
            return VirtualFileSystem(path, create=True)
        return None


def _interactive_filesystem() -> None:
    disk_path = _default_disk_path()
    _banner("BONUS - MINI SYSTEME DE FICHIERS A INODES")
    print("Image disque : %s" % disk_path)
    while True:
        print("\n1) Creer  2) Lire  3) Supprimer  4) Lister  5) Table d'inodes")
        print("6) Etat disque  7) Reformater  0) Retour")
        choice = _ask("Choix", "4")
        if choice == "0":
            return
        try:
            fs = _open_interactive_disk(disk_path)
            if fs is None:
                return
            if choice == "1":
                name = _ask("Nom du fichier")
                content = _ask("Contenu")
                inode = fs.create(name, content)
                print("Fichier cree dans l'inode %d." % inode.inode_id)
            elif choice == "2":
                print(fs.read(_ask("Nom du fichier")))
            elif choice == "3":
                name = _ask("Nom du fichier")
                if _ask_yes_no("Supprimer '%s' ?" % name):
                    fs.delete(name)
                    print("Fichier supprime et blocs liberes.")
            elif choice == "4":
                _print_files(fs)
            elif choice == "5":
                _print_inodes(fs)
            elif choice == "6":
                status = fs.status()
                print(
                    "Blocs : %(used_blocks)d/%(block_count)d occupes | "
                    "Inodes : %(used_inodes)d/%(max_inodes)d occupes" % status
                )
            elif choice == "7":
                if _ask_yes_no("Reformater le disque virtuel et perdre ses fichiers ?"):
                    fs.format()
                    print("Disque virtuel reformate.")
            else:
                print("Choix inconnu.")
        except FileSystemError as error:
            print("Erreur : %s" % error)


def interactive_menu() -> int:
    """Lance le menu integre demande par le sujet."""

    while True:
        _banner("ESINOS - MINI-NOYAU SIMULE")
        print("1) Ordonnancement CPU")
        print("2) Memoire virtuelle (FIFO/LRU/Optimal)")
        print("3) Traduction, TLB et EAT")
        print("4) Bonus : systeme de fichiers a inodes")
        print("5) Demonstration automatique")
        print("0) Quitter")
        choice = _ask("Choix", "5")
        try:
            if choice == "0":
                print("Au revoir.")
                return 0
            if choice == "1":
                _interactive_scheduler()
            elif choice == "2":
                _interactive_replacement()
            elif choice == "3":
                _interactive_translation()
            elif choice == "4":
                _interactive_filesystem()
            elif choice == "5":
                run_demo()
            else:
                print("Choix inconnu.")
        except KeyboardInterrupt:
            print("\nRetour au menu.")


def run_demo() -> int:
    """Execute un scenario deterministe couvrant les demonstrations du sujet."""

    _banner("ESINOS : DEMONSTRATION INTEGREE")
    print("Priorite : plus le nombre est petit, plus le processus est prioritaire.\n")

    _banner("1. ORDONNANCEMENT - GANTT FCFS / SJF / RR / PRIORITY")
    for algorithm, quantum in (("fcfs", None), ("sjf", None), ("rr", 2), ("priority", None)):
        print(format_schedule(run_scheduler(SAMPLE_PROCESSES, algorithm, quantum)))
        print()

    _banner("2. PAGINATION - FIFO PAS A PAS, PUIS COMPARAISON LRU / OPTIMAL")
    print("References : %s | Cadres : 3\n" % ", ".join(map(str, SAMPLE_REFERENCES)))
    fifo = simulate_page_replacement(SAMPLE_REFERENCES, 3, "fifo")
    lru = simulate_page_replacement(SAMPLE_REFERENCES, 3, "lru")
    optimal = simulate_page_replacement(SAMPLE_REFERENCES, 3, "optimal")
    print(format_replacement(fifo))
    print(
        "\nComparaison : FIFO = %d defauts, LRU = %d, Optimal = %d."
        % (fifo.page_faults, lru.page_faults, optimal.page_faults)
    )

    _banner("3. TRADUCTION D'ADRESSES, TLB ET EAT")
    manager = VirtualMemoryManager(64, SAMPLE_PAGE_TABLE, tlb_capacity=2)
    for address in SAMPLE_ADDRESSES:
        print(format_translation(manager.translate(address)))
    print("\n" + format_tlb(manager))
    print("EAT avec t_TLB=10 ns, t_mem=100 ns : %.2f ns" % manager.effective_access_time(10, 100))

    _banner("4. BONUS - INODES, CREATION / LECTURE / SUPPRESSION")
    with tempfile.TemporaryDirectory(prefix="esinos-demo-") as temporary_directory:
        disk = Path(temporary_directory) / "demo.disk.json"
        fs = VirtualFileSystem(disk, block_count=12, block_size=16, inode_count=4, create=True)
        inode = fs.create("notes.txt", "Bonjour depuis le disque virtuel ESINOS.")
        print("Creation : notes.txt -> inode %d, blocs %s" % (inode.inode_id, list(inode.blocks)))
        print("Lecture : %s" % fs.read("notes.txt"))
        print("\nTable d'inodes apres creation :")
        _print_inodes(fs)
        fs.delete("notes.txt")
        print("\nSuppression de notes.txt : les blocs sont de nouveau libres.")
        _print_inodes(fs)
    print("\nDemonstration terminee : l'image temporaire a ete supprimee proprement.")
    return 0


def _run_scheduler_command(args: argparse.Namespace) -> int:
    processes = parse_processes(args.processes)
    print(format_schedule(run_scheduler(processes, args.algorithm, args.quantum)))
    return 0


def _run_memory_command(args: argparse.Namespace) -> int:
    result = simulate_page_replacement(parse_references(args.references), args.frames, args.algorithm)
    print(format_replacement(result))
    return 0


def _run_translate_command(args: argparse.Namespace) -> int:
    manager = VirtualMemoryManager(args.page_size, parse_page_table(args.page_table), args.tlb_size)
    for address in parse_references(args.addresses):
        print(format_translation(manager.translate(address)))
    print("\n" + format_tlb(manager))
    print("EAT : %.2f ns" % manager.effective_access_time(args.tlb_time, args.memory_time))
    return 0


def _run_filesystem_command(args: argparse.Namespace) -> int:
    path = Path(args.disk)
    if args.fs_action == "init":
        VirtualFileSystem.initialize_new(
            path,
            block_count=args.blocks,
            block_size=args.block_size,
            inode_count=args.inodes,
        )
        print("Disque virtuel initialise : %s" % path)
        return 0

    fs = VirtualFileSystem(path)
    if args.fs_action == "create":
        inode = fs.create(args.name, args.content)
        print("Cree : %s (inode %d, blocs %s)" % (inode.name, inode.inode_id, list(inode.blocks)))
    elif args.fs_action == "read":
        print(fs.read(args.name))
    elif args.fs_action == "delete":
        fs.delete(args.name)
        print("Supprime : %s" % args.name)
    elif args.fs_action == "list":
        _print_files(fs)
    elif args.fs_action == "inodes":
        _print_inodes(fs)
    elif args.fs_action == "status":
        for name, value in fs.status().items():
            print("%s : %s" % (name, value))
    else:
        raise FileSystemError("Action systeme de fichiers inconnue.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="esinos",
        description="Simulation pedagogique d'un ordonnanceur, de la memoire et d'un mini FS.",
    )
    parser.add_argument("--version", action="version", version="ESINOS 1.0.0")
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("interactive", help="ouvrir le menu integre")
    commands.add_parser("demo", help="lancer une demonstration reproductible")

    scheduler = commands.add_parser("scheduler", help="simuler un ordonnanceur")
    scheduler.add_argument("--processes", required=True, help="PID:arrivee:burst[:priorite],...")
    scheduler.add_argument(
        "--algorithm",
        required=True,
        choices=["fcfs", "sjf", "rr", "priority"],
    )
    scheduler.add_argument("--quantum", type=int, help="quantum obligatoire pour rr")

    memory = commands.add_parser("memory", help="simuler un remplacement de pages")
    memory.add_argument("--references", required=True, help="suite de pages separees par des virgules")
    memory.add_argument("--frames", required=True, type=int, help="nombre de cadres")
    memory.add_argument("--algorithm", required=True, choices=["fifo", "lru", "optimal"])

    translation = commands.add_parser("translate", help="traduire des adresses avec un TLB")
    translation.add_argument("--page-size", required=True, type=int)
    translation.add_argument("--page-table", required=True, help="page:cadre,page:cadre")
    translation.add_argument("--addresses", required=True, help="adresses separees par des virgules")
    translation.add_argument("--tlb-size", type=int, default=2)
    translation.add_argument("--tlb-time", type=float, default=10.0)
    translation.add_argument("--memory-time", type=float, default=100.0)

    filesystem = commands.add_parser("fs", help="operer le mini systeme de fichiers")
    filesystem.add_argument("--disk", default="data/esinos.disk.json", help="image disque JSON")
    filesystem.add_argument("--blocks", type=int, default=64, help="nombre de blocs a l'initialisation")
    filesystem.add_argument("--block-size", type=int, default=64, help="taille des blocs a l'initialisation")
    filesystem.add_argument("--inodes", type=int, default=16, help="nombre d'inodes a l'initialisation")
    fs_actions = filesystem.add_subparsers(dest="fs_action", required=True)
    fs_actions.add_parser("init", help="creer une image disque neuve sans ecraser")
    create = fs_actions.add_parser("create", help="creer un fichier")
    create.add_argument("name")
    create.add_argument("content")
    read = fs_actions.add_parser("read", help="lire un fichier")
    read.add_argument("name")
    delete = fs_actions.add_parser("delete", help="supprimer un fichier")
    delete.add_argument("name")
    fs_actions.add_parser("list", help="lister les fichiers")
    fs_actions.add_parser("inodes", help="afficher la table d'inodes")
    fs_actions.add_parser("status", help="afficher l'etat du disque")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Point d'entree commun du menu et des sous-commandes."""

    parser = build_parser()
    args = parser.parse_args(argv)
    actions = {
        "scheduler": _run_scheduler_command,
        "memory": _run_memory_command,
        "translate": _run_translate_command,
        "fs": _run_filesystem_command,
    }
    try:
        if args.command in {None, "interactive"}:
            return interactive_menu()
        if args.command == "demo":
            return run_demo()
        return actions[args.command](args)
    except (SchedulerError, VirtualMemoryError, FileSystemError, OSError, ValueError) as error:
        print("Erreur : %s" % error, file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\nExecution interrompue.", file=sys.stderr)
        return 130
