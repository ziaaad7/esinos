"""Lancement du menu et de la démonstration ESINOS."""
import argparse
import os
import sys
from . import __version__
from .menus import menu_cpu, menu_remplacement, menu_traduction, menu_eat_defauts
from .menus import menu_disque as ouvrir_menu_disque, demonstration
from .entrees import demander_choix, lire_processus
from .sorties import titre

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


def main(argv=None):
    parser = argparse.ArgumentParser(description="ESINOS - mini-noyau simulé")
    parser.add_argument("commande", nargs="?", default="interactive",
                        choices=["interactive", "demo"])
    parser.add_argument("--version", action="version", version="ESINOS " + __version__)
    choix = parser.parse_args(argv)
    try:
        if choix.commande == "demo":
            demonstration()
        else:
            menu()
        return 0
    except (OSError, ValueError) as erreur:
        print("Erreur :", erreur, file=sys.stderr)
        return 2
    except (KeyboardInterrupt, EOFError):
        print("\nAu revoir.")
        return 0
