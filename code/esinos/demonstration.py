"""Scénarios reproductibles, avec une image disque temporaire."""
import os
from tempfile import TemporaryDirectory
from .exemples import PROCESSUS, PAGES, ADRESSES, TABLE
from .entrees import lire_processus, liste_entiers, lire_table
from .sorties import titre, comparer_cpu, afficher_cpu, afficher_remplacement
from .sorties import comparer_remplacement, afficher_traduction, afficher_eat_defauts
from .sorties import afficher_inodes
from .filesystem import initialiser, creer_fichier, lire_fichier, supprimer_fichier
from .carte_disque import carte_blocs, explication_fichier


def demonstration(mode="resume"):
    titre("ESINOS - DÉMONSTRATION")
    processus = lire_processus(PROCESSUS)
    comparer_cpu(processus, 2)
    if mode != "resume":
        afficher_cpu(processus, "rr", 2, mode)

    pages = liste_entiers(PAGES)
    afficher_remplacement(pages, 3, "fifo", mode)
    comparer_remplacement(pages, 3)
    afficher_traduction(liste_entiers(ADRESSES), 64, lire_table(TABLE), 2,
                        mode=mode)

    afficher_eat_defauts(0.001, 100, 1000000)

    with TemporaryDirectory() as dossier:
        chemin = os.path.join(dossier, "demo.disk.img")
        initialiser(chemin, 12, 16, 4)
        creer_fichier(chemin, "notes.txt",
                      "Bonjour depuis le disque virtuel ESINOS.")
        titre("BONUS - INODES ET BLOCS")
        afficher_inodes(chemin)
        print(explication_fichier(chemin, "notes.txt"))
        print("Lecture :", lire_fichier(chemin, "notes.txt"))
        print(carte_blocs(chemin))
        supprimer_fichier(chemin, "notes.txt")
        print("Après suppression :")
        afficher_inodes(chemin)
        print(carte_blocs(chemin))
