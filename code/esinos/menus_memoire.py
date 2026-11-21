"""Parcours de remplacement de pages et de traduction d'adresses."""
from .exemples import PAGES, ADRESSES, TABLE
from .entrees import liste_entiers, lire_table, lire_avec_defaut
from .entrees import demander_choix, demander_entier, demander_temps
from .entrees import demander_liste, choisir_mode
from .sorties import titre, afficher_remplacement, comparer_remplacement
from .sorties import afficher_traduction, afficher_eat_defauts


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
            afficher_remplacement(pages, cadres, algorithmes[choix], choisir_mode())


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
                                temps_tlb, temps_memoire, choisir_mode())
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
