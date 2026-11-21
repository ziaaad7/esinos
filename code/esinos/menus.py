"""Menus, exemples et démonstration du simulateur."""
import os
from tempfile import TemporaryDirectory
from .entrees import lire_processus, lire_avec_defaut, lire_table, liste_entiers
from .entrees import demander_choix, demander_entier, demander_temps
from .entrees import demander_liste
from .sorties import titre, afficher_cpu, comparer_cpu, afficher_remplacement
from .sorties import comparer_remplacement, afficher_traduction, afficher_eat_defauts
from .sorties import afficher_fichiers, afficher_inodes, afficher_etat
from .affichage import tableau_texte
from .filesystem import initialiser, creer_fichier, lire_fichier
from .filesystem import supprimer_fichier, reformater, migrer_json, format_disque
from .carte_disque import carte_blocs, explication_fichier

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


def menu_eat_defauts():
    titre("EAT AVEC DÉFAUTS DE PAGE")
    print("Un défaut inclut tout son traitement, dans la même unité ns.")
    while True:
        taux = demander_temps("Taux de défaut p (0 à 1)", 0.001)
        if taux <= 1:
            break
        print("Le taux doit être compris entre 0 et 1.")
    memoire = demander_temps("Temps mémoire en ns", 100)
    defaut = demander_temps("Traitement total d'un défaut en ns", 1000000)
    afficher_eat_defauts(taux, memoire, defaut)


def menu_disque(chemin):
    if not os.path.exists(chemin):
        initialiser(chemin)
    while True:
        titre("SYSTÈME DE FICHIERS À INODES")
        print("Image :", chemin)
        print("1 Créer | 2 Lire | 3 Supprimer | 4 Lister | 5 Inodes")
        print("6 État | 7 Reformater | 8 Carte des blocs | 9 Suivre un fichier")
        print("10 Copier une ancienne image JSON en binaire")
        print("0 Retour")
        choix = demander_choix("Choix", ("0", "1", "2", "3", "4", "5",
                                        "6", "7", "8", "9", "10"), "4")
        try:
            if choix == "0":
                return
            if choix == "1":
                nom = input("Nom : ").strip()
                texte = input("Texte : ")
                inode = creer_fichier(chemin, nom, texte)
                print(f"Fichier créé dans l'inode {inode['numero']}.")
                print(explication_fichier(chemin, nom))
            elif choix == "2":
                print(lire_fichier(chemin, input("Nom : ").strip()))
            elif choix == "3":
                nom = input("Nom : ").strip()
                if input("Supprimer ce fichier ? [oui/non] : ").strip().lower() == "oui":
                    supprimer_fichier(chemin, nom)
                    print("Fichier supprimé. Ses blocs et son inode sont libres.")
                else:
                    print("Action annulée.")
            elif choix == "4":
                afficher_fichiers(chemin)
            elif choix == "5":
                afficher_inodes(chemin)
            elif choix == "6":
                afficher_etat(chemin)
            elif choix == "7":
                reponse = input("Effacer tous les fichiers virtuels ? [oui/non] : ")
                if reponse.strip().lower() == "oui":
                    reformater(chemin)
                    print("Disque reformaté.")
                else:
                    print("Action annulée.")
            elif choix == "8":
                print(carte_blocs(chemin))
            elif choix == "9":
                print(explication_fichier(chemin, input("Nom : ").strip()))
            elif choix == "10":
                if format_disque(chemin) == "binaire":
                    print("Cette image utilise déjà le format binaire.")
                else:
                    propose = os.path.splitext(chemin)[0] + ".img"
                    destination = lire_avec_defaut("Nouveau chemin .img", propose)
                    migrer_json(chemin, destination)
                    chemin = destination
                    print("Copie binaire ouverte. Le JSON original est conservé.")
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
