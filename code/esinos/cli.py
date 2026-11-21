"""Point d'entrée : routage des menus et commandes du Terminal."""
import argparse
import os
import sys
from . import __version__
from .exemples import PROCESSUS, PAGES, ADRESSES, TABLE
from .entrees import lire_processus, liste_entiers, lire_table, demander_choix
from .sorties import titre, afficher_cpu, afficher_remplacement, afficher_traduction
from .sorties import afficher_fichiers, afficher_inodes, afficher_etat
from .sorties import afficher_eat_defauts
from .menus_cpu import menu_cpu, saisir_processus
from .menus_memoire import menu_remplacement, menu_traduction, menu_eat_defauts
from .menus_fichiers import menu_disque as ouvrir_menu_disque
from .demonstration import demonstration
from .filesystem import initialiser, creer_fichier, lire_fichier
from .filesystem import supprimer_fichier, migrer_json
from .carte_disque import carte_blocs, explication_fichier

DOSSIER_CODE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGE = os.path.join(DOSSIER_CODE, "data", "esinos.disk.img")
ANCIENNE_IMAGE = os.path.join(DOSSIER_CODE, "data", "esinos.disk.json")
if not os.path.exists(IMAGE) and os.path.exists(ANCIENNE_IMAGE):
    IMAGE = ANCIENNE_IMAGE


def menu_disque():
    # La fonction reste importable pour les scripts et les tests de la version 2.
    return ouvrir_menu_disque(IMAGE)


def menu():
    while True:
        titre("ESINOS - MINI-NOYAU SIMULÉ")
        print("1 Ordonnancement CPU")
        print("2 Remplacement de pages")
        print("3 Traduction, TLB et EAT")
        print("4 Système de fichiers à inodes")
        print("5 Démonstration | 6 EAT avec défauts de page | 0 Quitter")
        choix = demander_choix("Choix", ("0", "1", "2", "3", "4", "5", "6"), "5")
        try:
            if choix == "0":
                return
            if choix == "1":
                menu_cpu()
            elif choix == "2":
                menu_remplacement()
            elif choix == "3":
                menu_traduction()
            elif choix == "4":
                menu_disque()
            elif choix == "5":
                demonstration()
            elif choix == "6":
                menu_eat_defauts()
        except (OSError, ValueError) as erreur:
            print("Erreur :", erreur)


def arguments():
    # argparse lit les options du Terminal et produit aussi l'aide --help.
    parser = argparse.ArgumentParser(description="ESINOS - mini-noyau simulé")
    parser.add_argument("--version", action="version", version="ESINOS " + __version__)
    commandes = parser.add_subparsers(dest="commande")
    commandes.add_parser("interactive", help="ouvrir le menu")
    demo = commandes.add_parser("demo", help="lancer les exemples")
    demo.add_argument("--explain", action="store_true",
                      help="expliquer les décisions")

    cpu = commandes.add_parser("scheduler", help="simuler le CPU")
    cpu.add_argument("--processes", required=True)
    cpu.add_argument("--algorithm", required=True,
                     choices=["fcfs", "sjf", "rr", "priority", "priorite"])
    cpu.add_argument("--quantum", type=int)
    cpu.add_argument("--explain", action="store_true",
                         help="expliquer les décisions")

    memoire = commandes.add_parser("memory", help="remplacer des pages")
    memoire.add_argument("--references", required=True)
    memoire.add_argument("--frames", required=True, type=int)
    memoire.add_argument("--algorithm", required=True,
                         choices=["fifo", "lru", "optimal"])
    memoire.add_argument("--explain", action="store_true",
                         help="expliquer les décisions")

    traduction = commandes.add_parser("translate", help="traduire des adresses")
    traduction.add_argument("--page-size", required=True, type=int)
    traduction.add_argument("--page-table", required=True)
    traduction.add_argument("--addresses", required=True)
    traduction.add_argument("--tlb-size", type=int, default=2)
    traduction.add_argument("--tlb-time", type=float, default=10)
    traduction.add_argument("--memory-time", type=float, default=100)
    traduction.add_argument("--explain", action="store_true",
                         help="expliquer les décisions")

    eat = commandes.add_parser("eat", help="EAT avec défauts de page")
    eat.add_argument("--fault-rate", type=float, required=True)
    eat.add_argument("--memory-time", type=float, default=100)
    eat.add_argument("--fault-time", type=float, default=1000000)

    disque = commandes.add_parser("fs", help="gérer le disque virtuel")
    disque.add_argument("--disk", default=IMAGE)
    disque.add_argument("--blocks", type=int, default=64)
    disque.add_argument("--block-size", type=int, default=64)
    disque.add_argument("--inodes", type=int, default=16)
    actions = disque.add_subparsers(dest="action", required=True)
    actions.add_parser("init")
    creation = actions.add_parser("create")
    creation.add_argument("name")
    creation.add_argument("content")
    lecture = actions.add_parser("read")
    lecture.add_argument("name")
    suppression = actions.add_parser("delete")
    suppression.add_argument("name")
    actions.add_parser("list")
    actions.add_parser("inodes")
    actions.add_parser("status")
    actions.add_parser("map", help="voir les blocs libres et occupés")
    parcours = actions.add_parser("explain", help="suivre un fichier dans le disque")
    parcours.add_argument("name")
    migration = actions.add_parser("migrate", help="copier un JSON en image binaire")
    migration.add_argument("destination")
    return parser


def main(argv=None):
    choix = arguments().parse_args(argv)
    try:
        if choix.commande is None or choix.commande == "interactive":
            menu()
        elif choix.commande == "demo":
            demonstration("explique" if choix.explain else "resume")
        elif choix.commande == "scheduler":
            politique = choix.algorithm
            if politique == "priority":
                politique = "priorite"
            quantum = choix.quantum
            if politique == "rr" and quantum is None:
                raise ValueError("Round Robin exige --quantum.")
            mode = "explique" if choix.explain else "resume"
            afficher_cpu(lire_processus(choix.processes), politique, quantum, mode)
        elif choix.commande == "memory":
            afficher_remplacement(liste_entiers(choix.references),
                                   choix.frames, choix.algorithm,
                                   "explique" if choix.explain else "resume")
        elif choix.commande == "translate":
            afficher_traduction(liste_entiers(choix.addresses), choix.page_size,
                                lire_table(choix.page_table), choix.tlb_size,
                                choix.tlb_time, choix.memory_time,
                                "explique" if choix.explain else "resume")
        elif choix.commande == "eat":
            afficher_eat_defauts(choix.fault_rate, choix.memory_time, choix.fault_time)
        elif choix.commande == "fs":
            chemin = choix.disk
            if choix.action == "init":
                initialiser(chemin, choix.blocks, choix.block_size, choix.inodes)
                print("Disque initialisé :", chemin)
            elif choix.action == "create":
                inode = creer_fichier(chemin, choix.name, choix.content)
                print("Fichier créé :", inode)
            elif choix.action == "read":
                print(lire_fichier(chemin, choix.name))
            elif choix.action == "delete":
                supprimer_fichier(chemin, choix.name)
                print("Fichier supprimé.")
            elif choix.action == "list":
                afficher_fichiers(chemin)
            elif choix.action == "inodes":
                afficher_inodes(chemin)
            elif choix.action == "status":
                afficher_etat(chemin)
            elif choix.action == "map":
                print(carte_blocs(chemin))
            elif choix.action == "explain":
                print(explication_fichier(chemin, choix.name))
            elif choix.action == "migrate":
                migrer_json(chemin, choix.destination)
                print("Copie binaire créée :", choix.destination)
        return 0
    except (OSError, ValueError) as erreur:
        print("Erreur :", erreur, file=sys.stderr)
        return 2
    except (KeyboardInterrupt, EOFError):
        print("\nAu revoir.")
        return 0
