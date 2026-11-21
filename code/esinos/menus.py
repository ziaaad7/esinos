"""Menus, exemples et démonstration du simulateur."""
import os
from tempfile import TemporaryDirectory
from .entrees import lire_processus, lire_avec_defaut, lire_table, liste_entiers
from .entrees import demander_choix, demander_entier, demander_temps
from .entrees import demander_liste
from .sorties import titre, afficher_cpu, comparer_cpu, afficher_remplacement
from .sorties import comparer_remplacement, afficher_traduction
from .sorties import afficher_inodes
from .affichage import tableau_texte
from .filesystem import initialiser, creer_fichier, lire_fichier
from .filesystem import supprimer_fichier

PROCESSUS = "P1:0:7:2,P2:2:4:1,P3:4:1:3,P4:5:4:2"
PAGES = "7,0,1,2,0,3,0,4,2,3,0,3,2"
ADRESSES = "5,70,75,130,5,195,70,260"
TABLE = "0:5,1:2,2:7,3:1"


def saisir_processus():
    nombre = demander_entier("Nombre de processus", 4, 1)
    processus = []
    noms = []
    for index in range(nombre):
        while True:
            nom = lire_avec_defaut(f"Nom du processus {index + 1}", f"P{index + 1}")
            if nom.upper() != "IDLE" and nom not in noms:
                break
            print("Ce nom est réservé ou déjà utilisé.")
        arrivee = demander_entier("Instant d'arrivée AT", 0, 0)
        duree = demander_entier("Durée CPU BT", 1, 1)
        priorite = demander_entier("Priorité (petit nombre = plus urgente)", 0, None)
        processus.append({"nom": nom, "arrivee": arrivee,
                          "duree": duree, "priorite": priorite})
        noms.append(nom)
    return processus


def menu_cpu():
    processus = lire_processus(PROCESSUS)
    while True:
        titre("ORDONNANCEMENT CPU")
        lignes = []
        for p in processus:
            lignes.append((p["nom"], p["arrivee"], p["duree"], p["priorite"]))
        print(tableau_texte(("PID", "AT", "BT", "Prio"), lignes))
        print("1 FCFS | 2 SJF | 3 Round Robin | 4 Priority | 5 Comparer")
        print("6 Saisir des processus | 7 Exemple | 0 Retour")
        choix = demander_choix("Choix", ("0", "1", "2", "3", "4", "5", "6", "7"), "1")
        if choix == "0":
            return
        if choix == "6":
            processus = saisir_processus()
        elif choix == "7":
            processus = lire_processus(PROCESSUS)
        else:
            quantum = 2
            if choix in ("3", "5"):
                quantum = demander_entier("Quantum Round Robin", 2, 1)
            if choix == "5":
                comparer_cpu(processus, quantum)
            else:
                algorithmes = {"1": "fcfs", "2": "sjf", "3": "rr", "4": "priorite"}
                afficher_cpu(processus, algorithmes[choix], quantum)


def menu_remplacement():
    pages = liste_entiers(PAGES)
    cadres = 3
    while True:
        titre("REMPLACEMENT DE PAGES")
        print("Références :", pages)
        print("Nombre de cadres :", cadres)
        print("1 FIFO | 2 LRU | 3 Optimal | 4 Comparer")
        print("5 Modifier les pages et les cadres | 6 Exemple | 0 Retour")
        choix = demander_choix("Choix", ("0", "1", "2", "3", "4", "5", "6"), "1")
        if choix == "0":
            return
        if choix == "5":
            texte = " ".join(map(str, pages))
            pages = demander_liste("Pages (espaces ou virgules)", texte)
            cadres = demander_entier("Nombre de cadres", cadres, 1)
        elif choix == "6":
            pages, cadres = liste_entiers(PAGES), 3
        elif choix == "4":
            comparer_remplacement(pages, cadres)
        else:
            algorithmes = {"1": "fifo", "2": "lru", "3": "optimal"}
            afficher_remplacement(pages, cadres, algorithmes[choix])


def menu_traduction():
    adresses = liste_entiers(ADRESSES)
    taille, table, capacite = 64, lire_table(TABLE), 2
    temps_tlb, temps_memoire = 10, 100
    while True:
        titre("TRADUCTION D'ADRESSES")
        print("Adresses :", adresses)
        print(f"Taille de page : {taille} octets | Capacité TLB : {capacite}")
        print("Table page -> cadre :", table)
        print("1 Lancer | 2 Modifier les paramètres | 3 Exemple | 0 Retour")
        choix = demander_choix("Choix", ("0", "1", "2", "3"), "1")
        if choix == "0":
            return
        if choix == "1":
            afficher_traduction(adresses, taille, table, capacite,
                                temps_tlb, temps_memoire)
        elif choix == "2":
            adresses = demander_liste("Adresses", " ".join(map(str, adresses)))
            taille = demander_entier("Taille de page en octets", taille, 1)
            paires = []
            for page, cadre in table.items():
                paires.append(f"{page}:{cadre}")
            while True:
                try:
                    texte = lire_avec_defaut("Table page:cadre", ",".join(paires))
                    table = lire_table(texte)
                    break
                except ValueError as erreur:
                    print("Erreur :", erreur)
            capacite = demander_entier("Capacité du TLB (0 = désactivé)", capacite, 0)
            temps_tlb = demander_temps("Temps TLB en ns", temps_tlb)
            temps_memoire = demander_temps("Temps mémoire en ns", temps_memoire)
        else:
            adresses, taille = liste_entiers(ADRESSES), 64
            table, capacite = lire_table(TABLE), 2
            temps_tlb, temps_memoire = 10, 100


def menu_disque(chemin):
    if not os.path.exists(chemin):
        initialiser(chemin)
    while True:
        titre("SYSTÈME DE FICHIERS À INODES")
        print("1 Créer | 2 Lire | 3 Supprimer | 4 Table d'inodes | 0 Retour")
        choix = demander_choix("Choix", ("0", "1", "2", "3", "4"), "4")
        try:
            if choix == "0":
                return
            if choix == "1":
                nom = input("Nom : ").strip()
                texte = input("Texte : ")
                inode = creer_fichier(chemin, nom, texte)
                print(f"Fichier créé dans l'inode {inode['numero']}.")
            elif choix == "2":
                print(lire_fichier(chemin, input("Nom : ").strip()))
            elif choix == "3":
                nom = input("Nom : ").strip()
                reponse = input("Supprimer ce fichier ? [oui/non] : ")
                if reponse.strip().lower() == "oui":
                    supprimer_fichier(chemin, nom)
                    print("Fichier supprimé. Ses blocs et son inode sont libres.")
                else:
                    print("Action annulée.")
            else:
                afficher_inodes(chemin)
        except (OSError, ValueError) as erreur:
            print("Erreur :", erreur)


def demonstration():
    titre("ESINOS - DÉMONSTRATION")
    processus = lire_processus(PROCESSUS)
    comparer_cpu(processus, 2)
    pages = liste_entiers(PAGES)
    afficher_remplacement(pages, 3, "fifo")
    comparer_remplacement(pages, 3)
    afficher_traduction(liste_entiers(ADRESSES), 64, lire_table(TABLE), 2)

    with TemporaryDirectory() as dossier:
        chemin = os.path.join(dossier, "demo.disk.json")
        initialiser(chemin, 12, 16, 4)
        creer_fichier(chemin, "notes.txt",
                      "Bonjour depuis le disque virtuel ESINOS.")
        titre("BONUS - INODES ET BLOCS")
        afficher_inodes(chemin)
        print("Lecture :", lire_fichier(chemin, "notes.txt"))
        supprimer_fichier(chemin, "notes.txt")
        print("Après suppression :")
        afficher_inodes(chemin)
