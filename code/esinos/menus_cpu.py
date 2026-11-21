"""Parcours interactif CPU, avec conservation des processus courants."""
from .exemples import PROCESSUS
from .entrees import lire_processus, lire_avec_defaut, demander_entier
from .entrees import demander_choix, choisir_mode
from .sorties import titre, afficher_cpu, comparer_cpu
from .affichage import tableau_texte


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
