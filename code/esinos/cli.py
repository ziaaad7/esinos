import argparse
import os
import sys
from tempfile import TemporaryDirectory

from .filesystem import initialiser, creer_fichier, lire_fichier
from .filesystem import supprimer_fichier, lister_inodes
from .filesystem import etat_disque, reformater
from .memory import remplacer, traduire, calculer_eat
from .scheduler import ordonnancer


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
    for morceau in texte.split(","):
        nombre = int(morceau)
        if nombre < 0:
            raise ValueError("Les numéros et les adresses commencent à zéro.")
        valeurs.append(nombre)
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


def afficher_cpu(processus, algorithme, quantum=2):
    gantt, lignes = ordonnancer(processus, algorithme, quantum)
    print("\n", algorithme.upper())
    print("Gantt :", end=" ")
    for index in range(len(gantt)):
        nom, debut, fin = gantt[index]
        print(f"{nom} [{debut}-{fin}]", end="")
        if index < len(gantt) - 1:
            print(" -> ", end="")
    print()
    print("PID | AT | BT | Prio | Fin (CT) | Attente | Séjour")
    attente_totale = 0
    sejour_total = 0
    for nom, arrivee, duree, priorite, fin, attente, sejour in lignes:
        print(nom, arrivee, duree, priorite, fin, attente, sejour, sep=" | ")
        attente_totale += attente
        sejour_total += sejour
    print(f"Attente moyenne : {attente_totale / len(lignes):.2f}")
    print(f"Séjour moyen : {sejour_total / len(lignes):.2f}")


def afficher_remplacement(pages, cadres, algorithme):
    defauts, trace = remplacer(pages, cadres, algorithme)
    print("Étape | Page | Résultat | Victime | Cadres")
    etape = 1
    for page, hit, victime, etat_cadres in trace:
        resultat = "défaut"
        if hit:
            resultat = "hit"
        print(etape, page, resultat, victime, etat_cadres, sep=" | ")
        etape += 1
    print(f"{algorithme.upper()} : {defauts} défauts")


def afficher_traduction(adresses, taille, table, capacite,
                        temps_tlb=10, temps_memoire=100):
    lignes, hits = traduire(adresses, taille, table, capacite)
    print("Adresse | Page | Déplacement | Cadre | Physique | TLB")
    for adresse, page, deplacement, cadre, physique, hit in lignes:
        resultat = "miss"
        if hit:
            resultat = "hit"
        if physique is None:
            resultat = "miss et défaut de page"
        print(adresse, page, deplacement, cadre, physique, resultat, sep=" | ")
    print(f"Hits TLB : {hits}/{len(lignes)}")
    eat = calculer_eat(hits, len(lignes), temps_tlb, temps_memoire)
    print(f"EAT : {eat:.2f} ns")


def afficher_inodes(chemin):
    print("Inode | Nom | Taille en octets | Blocs")
    inodes = lister_inodes(chemin)
    for index in range(len(inodes)):
        inode = inodes[index]
        if inode is None:
            print(index + 1, "libre", sep=" | ")
        else:
            print(inode["numero"], inode["nom"], inode["taille"],
                  inode["blocs"], sep=" | ")


def menu_disque():
    if not os.path.exists(IMAGE):
        initialiser(IMAGE)
    while True:
        print("\n1 Créer | 2 Lire | 3 Supprimer | 4 Lister | 5 Inodes")
        print("6 État disque | 7 Reformater | 0 Retour")
        choix = input("Choix : ").strip()
        try:
            if choix == "0":
                return
            elif choix == "1":
                nom = input("Nom : ").strip()
                texte = input("Texte : ")
                inode = creer_fichier(IMAGE, nom, texte)
                print("Blocs alloués", inode["blocs"])
            elif choix == "2":
                print(lire_fichier(IMAGE, input("Nom : ").strip()))
            elif choix == "3":
                nom = input("Nom : ").strip()
                if input("Supprimer ce fichier ? [oui/non] : ") == "oui":
                    supprimer_fichier(IMAGE, nom)
                    print("Fichier supprimé.")
            elif choix == "4":
                afficher_fichiers(IMAGE)
            elif choix == "5":
                afficher_inodes(IMAGE)
            elif choix == "6":
                afficher_etat(IMAGE)
            elif choix == "7":
                reponse = input("Effacer tous les fichiers virtuels ? [oui/non] : ")
                if reponse == "oui":
                    reformater(IMAGE)
                    print("Disque reformaté.")
            else:
                print("Choix inconnu.")
        except (OSError, ValueError) as erreur:
            print("Erreur :", erreur)


def demonstration():
    processus = lire_processus(PROCESSUS)
    for algorithme in ("fcfs", "sjf", "rr", "priorite"):
        afficher_cpu(processus, algorithme)

    pages = liste_entiers(PAGES)
    afficher_remplacement(pages, 3, "fifo")
    for algorithme in ("lru", "optimal"):
        defauts, _ = remplacer(pages, 3, algorithme)
        print(f"{algorithme.upper()} : {defauts} défauts")

    afficher_traduction(liste_entiers(ADRESSES), 64, lire_table(TABLE), 2)

    # Le dossier temporaire est nettoyé à la sortie de with.
    with TemporaryDirectory() as dossier:
        chemin = os.path.join(dossier, "demo.json")
        initialiser(chemin, 12, 16, 4)
        creer_fichier(chemin, "notes.txt",
                      "Bonjour depuis le disque virtuel ESINOS.")
        afficher_inodes(chemin)
        print("Lecture :", lire_fichier(chemin, "notes.txt"))
        supprimer_fichier(chemin, "notes.txt")
        afficher_inodes(chemin)


def menu():
    while True:
        print("\nESINOS - MINI-NOYAU SIMULÉ")
        print("1 CPU | 2 Remplacement | 3 Traduction | 4 Disque")
        print("5 Démonstration | 0 Quitter")
        choix = input("Choix : ").strip()
        try:
            if choix == "0":
                return
            elif choix == "1":
                texte = lire_avec_defaut("Nom:arrivée:durée:priorité", PROCESSUS)
                processus = lire_processus(texte)
                print("1) FCFS  2) SJF  3) Round Robin  4) Priority")
                politique = lire_avec_defaut("Algorithme (numéro ou nom)", "1")
                politique = politique.lower().strip()
                choix_cpu = {"1": "fcfs", "2": "sjf", "3": "rr", "4": "priorite"}
                politique = choix_cpu.get(politique, politique)
                if politique == "priority":
                    politique = "priorite"
                quantum = 2
                if politique == "rr":
                    quantum = int(lire_avec_defaut("Quantum", "2"))
                afficher_cpu(processus, politique, quantum)
            elif choix == "2":
                pages = liste_entiers(lire_avec_defaut("Pages", PAGES))
                cadres = int(lire_avec_defaut("Nombre de cadres", "3"))
                print("1) FIFO  2) LRU  3) Optimal")
                politique = lire_avec_defaut("Algorithme (numéro ou nom)", "1")
                choix_memoire = {"1": "fifo", "2": "lru", "3": "optimal"}
                politique = choix_memoire.get(politique, politique)
                afficher_remplacement(pages, cadres, politique)
            elif choix == "3":
                adresses = liste_entiers(lire_avec_defaut("Adresses", ADRESSES))
                taille = int(lire_avec_defaut("Taille de page", "64"))
                table = lire_table(lire_avec_defaut("Table page:cadre", TABLE))
                capacite = int(lire_avec_defaut("Capacité du TLB", "2"))
                temps_tlb = float(lire_avec_defaut("Temps TLB en ns", "10"))
                temps_memoire = float(lire_avec_defaut("Temps mémoire en ns", "100"))
                afficher_traduction(adresses, taille, table, capacite,
                                    temps_tlb, temps_memoire)
            elif choix == "4":
                menu_disque()
            elif choix == "5":
                demonstration()
            else:
                print("Choix inconnu.")
        except (OSError, ValueError) as erreur:
            print("Erreur :", erreur)


def afficher_fichiers(chemin):
    print("Inode | Nom | Taille en octets | Blocs")
    for inode in lister_inodes(chemin):
        if inode is not None:
            print(inode["numero"], inode["nom"], inode["taille"],
                  inode["blocs"], sep=" | ")


def afficher_etat(chemin):
    for nom, valeur in etat_disque(chemin).items():
        print(nom, valeur, sep=" : ")


def arguments():
    # argparse lit les options du Terminal et produit aussi l'aide --help.
    parser = argparse.ArgumentParser(description="ESINOS - mini-noyau simulé")
    parser.add_argument("--version", action="version", version="ESINOS 2.0.0")
    commandes = parser.add_subparsers(dest="commande")
    commandes.add_parser("interactive", help="ouvrir le menu")
    commandes.add_parser("demo", help="lancer les exemples")

    cpu = commandes.add_parser("scheduler", help="simuler le CPU")
    cpu.add_argument("--processes", required=True)
    cpu.add_argument("--algorithm", required=True,
                     choices=["fcfs", "sjf", "rr", "priority"])
    cpu.add_argument("--quantum", type=int)

    memoire = commandes.add_parser("memory", help="remplacer des pages")
    memoire.add_argument("--references", required=True)
    memoire.add_argument("--frames", required=True, type=int)
    memoire.add_argument("--algorithm", required=True,
                         choices=["fifo", "lru", "optimal"])

    traduction = commandes.add_parser("translate", help="traduire des adresses")
    traduction.add_argument("--page-size", required=True, type=int)
    traduction.add_argument("--page-table", required=True)
    traduction.add_argument("--addresses", required=True)
    traduction.add_argument("--tlb-size", type=int, default=2)
    traduction.add_argument("--tlb-time", type=float, default=10)
    traduction.add_argument("--memory-time", type=float, default=100)

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
    return parser


def main(argv=None):
    choix = arguments().parse_args(argv)
    try:
        if choix.commande is None or choix.commande == "interactive":
            menu()
        elif choix.commande == "demo":
            demonstration()
        elif choix.commande == "scheduler":
            politique = choix.algorithm
            if politique == "priority":
                politique = "priorite"
            quantum = choix.quantum
            if politique == "rr" and quantum is None:
                raise ValueError("Round Robin exige --quantum.")
            afficher_cpu(lire_processus(choix.processes), politique, quantum)
        elif choix.commande == "memory":
            afficher_remplacement(liste_entiers(choix.references),
                                   choix.frames, choix.algorithm)
        elif choix.commande == "translate":
            afficher_traduction(liste_entiers(choix.addresses), choix.page_size,
                                lire_table(choix.page_table), choix.tlb_size,
                                choix.tlb_time, choix.memory_time)
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
        return 0
    except (OSError, ValueError) as erreur:
        print("Erreur :", erreur, file=sys.stderr)
        return 2
    except (KeyboardInterrupt, EOFError):
        print("\nAu revoir.")
        return 0
