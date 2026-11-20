import argparse
import os
import sys
from math import isfinite
from tempfile import TemporaryDirectory

from .filesystem import initialiser, creer_fichier, lire_fichier
from .filesystem import supprimer_fichier, lister_inodes
from .filesystem import etat_disque, reformater
from .memory import remplacer, traduire, calculer_eat
from .scheduler import ordonnancer
from .affichage import gantt_texte, tableau_texte, explication_cpu
from .pedagogie import explications_remplacement, explications_traduction
from .carte_disque import carte_blocs, explication_fichier


# Ces valeurs sont proposées quand tu appuies sur Entrée.
PROCESSUS = "P1:0:7:2,P2:2:4:1,P3:4:1:3,P4:5:4:2"
PAGES = "7,0,1,2,0,3,0,4,2,3,0,3,2"
ADRESSES = "5,70,75,130,5,195,70,260"
TABLE = "0:5,1:2,2:7,3:1"
DOSSIER_CODE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGE = os.path.join(DOSSIER_CODE, "data", "esinos.disk.json")


def lire_avec_defaut(question, defaut):
    texte = input(f"{question} [{defaut}] : ").strip()
    if texte == "":
        return defaut
    return texte


def lire_processus(texte):
    processus = []
    noms = []
    for groupe in texte.split(","):
        champs = groupe.split(":")
        if len(champs) == 3:
            champs.append("0")
        if len(champs) != 4:
            raise ValueError("Utilise le format nom:arrivee:duree:priorite.")
        nom, arrivee, duree, priorite = champs
        nom = nom.strip()
        arrivee = int(arrivee)
        duree = int(duree)
        priorite = int(priorite)
        if nom == "" or nom.upper() == "IDLE" or nom in noms:
            raise ValueError("Choisis un nom unique, différent de IDLE.")
        if arrivee < 0 or duree <= 0:
            raise ValueError("L'arrivée doit être >= 0 et la durée > 0.")
        noms.append(nom)
        processus.append({
            "nom": nom, "arrivee": arrivee,
            "duree": duree, "priorite": priorite,
        })
    return processus


def liste_entiers(texte):
    valeurs = []
    for morceau in texte.replace(",", " ").split():
        nombre = int(morceau)
        if nombre < 0:
            raise ValueError("Les numéros et les adresses commencent à zéro.")
        valeurs.append(nombre)
    if not valeurs:
        raise ValueError("Saisis au moins un numéro.")
    return valeurs


def lire_table(texte):
    table = {}
    for paire in texte.split(","):
        champs = paire.split(":")
        if len(champs) != 2:
            raise ValueError("Utilise le format page:cadre,page:cadre.")
        page, cadre = int(champs[0]), int(champs[1])
        if page < 0 or cadre < 0 or page in table:
            raise ValueError("Une page unique et des numéros >= 0 sont requis.")
        table[page] = cadre
    return table


def titre(texte):
    print("\n" + texte)
    print("-" * len(texte))


def demander_choix(question, valeurs, defaut):
    while True:
        choix = lire_avec_defaut(question, defaut).lower()
        if choix in valeurs:
            return choix
        print("Choisis parmi :", ", ".join(valeurs))


def demander_entier(question, defaut, minimum=0):
    while True:
        try:
            valeur = int(lire_avec_defaut(question, str(defaut)))
            if minimum is None or valeur >= minimum:
                return valeur
            print(f"La valeur doit être au moins {minimum}.")
        except ValueError:
            print("Saisis un nombre entier.")


def demander_temps(question, defaut):
    while True:
        try:
            valeur = float(lire_avec_defaut(question, str(defaut)).replace(",", "."))
            if isfinite(valeur) and valeur >= 0:
                return valeur
        except ValueError:
            pass
        print("Saisis un temps fini, positif ou nul.")


def demander_liste(question, defaut):
    while True:
        try:
            return liste_entiers(lire_avec_defaut(question, defaut))
        except ValueError as erreur:
            print("Erreur :", erreur)


def choisir_mode():
    print("1 Résumé | 2 Expliqué | 3 Pas à pas")
    choix = demander_choix("Affichage", ("1", "2", "3"), "1")
    modes = {"1": "resume", "2": "explique", "3": "pasapas"}
    return modes[choix]


def parcourir_etapes(explications, mode):
    for explication in explications:
        print("\n" + explication)
        if mode == "pasapas":
            suite = input("Entrée : suite | t : tout afficher | 0 : retour : ")
            if suite.strip().lower() == "t":
                mode = "explique"
            elif suite.strip() == "0":
                return False
    return True


def afficher_cpu(processus, algorithme, quantum=2, mode="resume"):
    gantt, lignes = ordonnancer(processus, algorithme, quantum)
    titre(algorithme.upper())
    if mode != "resume":
        textes = explication_cpu(processus, gantt, algorithme, quantum)
        if not parcourir_etapes(textes, mode):
            return
    print(gantt_texte(gantt))
    print(tableau_texte(
        ("PID", "AT", "BT", "Prio", "Fin (CT)", "Attente", "Séjour"), lignes
    ))
    attente_totale = 0
    sejour_total = 0
    for ligne in lignes:
        attente_totale += ligne[5]
        sejour_total += ligne[6]
    print(f"Attente moyenne : {attente_totale / len(lignes):.2f}")
    print(f"Séjour moyen : {sejour_total / len(lignes):.2f}")


def comparer_cpu(processus, quantum=2):
    titre("COMPARAISON CPU - MÊMES PROCESSUS")
    resultats = []
    for algorithme in ("fcfs", "sjf", "rr", "priorite"):
        gantt, lignes = ordonnancer(processus, algorithme, quantum)
        print("\n" + algorithme.upper())
        print(gantt_texte(gantt))
        print(tableau_texte(
            ("PID", "AT", "BT", "Prio", "Fin (CT)", "Attente", "Séjour"), lignes
        ))
        attente = 0
        sejour = 0
        for ligne in lignes:
            attente += ligne[5]
            sejour += ligne[6]
        resultats.append((algorithme.upper(), f"{attente / len(lignes):.2f}",
                          f"{sejour / len(lignes):.2f}"))
    print(tableau_texte(("Algorithme", "Attente moyenne", "Séjour moyen"), resultats))
    print(f"Round Robin utilise un quantum de {quantum}.")


def afficher_remplacement(pages, cadres, algorithme, mode="resume"):
    defauts, trace = remplacer(pages, cadres, algorithme)
    titre(f"{algorithme.upper()} - {cadres} CADRES")
    if mode != "resume":
        textes = explications_remplacement(pages, cadres, algorithme, trace)
        if not parcourir_etapes(textes, mode):
            return
    lignes = []
    etape = 1
    for page, hit, victime, etat_cadres in trace:
        resultat = "défaut"
        if hit:
            resultat = "hit"
        lignes.append((etape, page, resultat, victime, str(etat_cadres)))
        etape += 1
    print(tableau_texte(("Étape", "Page", "Résultat", "Victime", "Cadres"), lignes))
    print(f"{algorithme.upper()} : {defauts} défauts")


def comparer_remplacement(pages, cadres):
    resultats = []
    for algorithme in ("fifo", "lru", "optimal"):
        defauts, trace = remplacer(pages, cadres, algorithme)
        taux = 0
        if pages:
            taux = 100 * defauts / len(pages)
        resultats.append((algorithme.upper(), defauts, len(pages) - defauts,
                          f"{taux:.2f} %"))
    titre(f"COMPARAISON MÉMOIRE - {cadres} CADRES")
    print(tableau_texte(("Algorithme", "Défauts", "Hits", "Taux de défaut"), resultats))


def afficher_traduction(adresses, taille, table, capacite,
                        temps_tlb=10, temps_memoire=100, mode="resume"):
    lignes, hits = traduire(adresses, taille, table, capacite)
    eat = calculer_eat(hits, len(lignes), temps_tlb, temps_memoire)
    titre("TRADUCTION, TLB ET EAT")
    if mode != "resume":
        textes = explications_traduction(adresses, taille, table, capacite, lignes)
        if not parcourir_etapes(textes, mode):
            return
    tableau = []
    for adresse, page, deplacement, cadre, physique, hit in lignes:
        resultat = "miss"
        if hit:
            resultat = "hit"
        if physique is None:
            resultat = "miss et défaut de page"
        tableau.append((adresse, page, deplacement, cadre, physique, resultat))
    print(tableau_texte(("Adresse", "Page", "Déplacement", "Cadre", "Physique", "TLB"),
                        tableau))
    print(f"Hits TLB : {hits}/{len(lignes)}")
    if mode != "resume":
        taux = hits / len(lignes)
        print(f"Chemin hit : {temps_tlb:g} + {temps_memoire:g} = "
              f"{temps_tlb + temps_memoire:g} ns")
        print(f"Chemin miss : {temps_tlb:g} + 2 x {temps_memoire:g} = "
              f"{temps_tlb + 2 * temps_memoire:g} ns")
        print(f"EAT = {taux:.3f} x coût hit + {1 - taux:.3f} x coût miss")
        print("Le délai de chargement d'une page depuis le disque est exclu.")
    print(f"EAT : {eat:.2f} ns")


def afficher_inodes(chemin):
    lignes = []
    inodes = lister_inodes(chemin)
    for index in range(len(inodes)):
        inode = inodes[index]
        if inode is None:
            lignes.append((index + 1, "libre", None, None, None))
        else:
            lignes.append((inode["numero"], "occupé", inode["nom"],
                           inode["taille"], str(inode["blocs"])))
    print(tableau_texte(("Inode", "État", "Nom", "Octets", "Blocs"), lignes))


def afficher_fichiers(chemin):
    lignes = []
    for inode in lister_inodes(chemin):
        if inode is not None:
            lignes.append((inode["numero"], inode["nom"], inode["taille"],
                           str(inode["blocs"])))
    print(tableau_texte(("Inode", "Nom", "Octets", "Blocs"), lignes))


def afficher_etat(chemin):
    etat = etat_disque(chemin)
    print(f"Blocs utilisés : {etat['blocs_utilises']}/{etat['nombre_blocs']}")
    print(f"Inodes utilisés : {etat['inodes_utilises']}/{etat['nombre_inodes']}")
    print(f"Taille d'un bloc : {etat['taille_bloc']} octets")


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
                afficher_cpu(processus, algorithmes[choix], quantum, choisir_mode())


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


def menu_disque():
    if not os.path.exists(IMAGE):
        initialiser(IMAGE)
    while True:
        titre("SYSTÈME DE FICHIERS À INODES")
        print("Image :", IMAGE)
        print("1 Créer | 2 Lire | 3 Supprimer | 4 Lister | 5 Inodes")
        print("6 État | 7 Reformater | 8 Carte des blocs | 9 Suivre un fichier")
        print("0 Retour")
        choix = demander_choix("Choix", ("0", "1", "2", "3", "4", "5",
                                        "6", "7", "8", "9"), "4")
        try:
            if choix == "0":
                return
            if choix == "1":
                nom = input("Nom : ").strip()
                texte = input("Texte : ")
                inode = creer_fichier(IMAGE, nom, texte)
                print(f"Fichier créé dans l'inode {inode['numero']}.")
                print(explication_fichier(IMAGE, nom))
            elif choix == "2":
                print(lire_fichier(IMAGE, input("Nom : ").strip()))
            elif choix == "3":
                nom = input("Nom : ").strip()
                if input("Supprimer ce fichier ? [oui/non] : ").strip().lower() == "oui":
                    supprimer_fichier(IMAGE, nom)
                    print("Fichier supprimé. Ses blocs et son inode sont libres.")
                else:
                    print("Action annulée.")
            elif choix == "4":
                afficher_fichiers(IMAGE)
            elif choix == "5":
                afficher_inodes(IMAGE)
            elif choix == "6":
                afficher_etat(IMAGE)
            elif choix == "7":
                reponse = input("Effacer tous les fichiers virtuels ? [oui/non] : ")
                if reponse.strip().lower() == "oui":
                    reformater(IMAGE)
                    print("Disque reformaté.")
                else:
                    print("Action annulée.")
            elif choix == "8":
                print(carte_blocs(IMAGE))
            elif choix == "9":
                print(explication_fichier(IMAGE, input("Nom : ").strip()))
        except (OSError, ValueError) as erreur:
            print("Erreur :", erreur)


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

    with TemporaryDirectory() as dossier:
        chemin = os.path.join(dossier, "demo.disk.json")
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


def menu():
    while True:
        titre("ESINOS - MINI-NOYAU SIMULÉ")
        print("1 Ordonnancement CPU")
        print("2 Remplacement de pages")
        print("3 Traduction, TLB et EAT")
        print("4 Système de fichiers à inodes")
        print("5 Démonstration | 0 Quitter")
        choix = demander_choix("Choix", ("0", "1", "2", "3", "4", "5"), "5")
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
        except (OSError, ValueError) as erreur:
            print("Erreur :", erreur)


def arguments():
    # argparse lit les options du Terminal et produit aussi l'aide --help.
    parser = argparse.ArgumentParser(description="ESINOS - mini-noyau simulé")
    parser.add_argument("--version", action="version", version="ESINOS 2.1.0")
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

    disque = commandes.add_parser("fs", help="gérer le disque virtuel")
    disque.add_argument("--disk", default="data/esinos.disk.json")
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
        return 0
    except (OSError, ValueError) as erreur:
        print("Erreur :", erreur, file=sys.stderr)
        return 2
    except (KeyboardInterrupt, EOFError):
        print("\nAu revoir.")
        return 0
