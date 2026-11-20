"""Ordonnanceur simple pour la version debutant d'ESINOS.

Les processus sont des dictionnaires avec quatre cles : nom, arrivee, duree
et priorite. La fonction publique retourne le Gantt et les lignes du tableau
de mesures, sans faire aucun affichage elle-meme.
"""


def fcfs(ordre):
    """Execute les processus deja tries par arrivee puis nom."""
    gantt = []
    horloge = 0

    for arrivee, nom, duree, priorite in ordre:
        if arrivee > horloge:
            gantt.append(("IDLE", horloge, arrivee))
            horloge = arrivee
        fin = horloge + duree
        gantt.append((nom, horloge, fin))
        horloge = fin

    return gantt


def sjf_ou_priorite(ordre, algorithme):
    """Execute SJF ou priorite sans interrompre une tranche commencee."""
    a_faire = ordre.copy()
    gantt = []
    horloge = 0

    while a_faire:
        choix = None
        meilleure_cle = None

        for processus in a_faire:
            arrivee, nom, duree, priorite = processus
            if arrivee <= horloge:
                if algorithme == "sjf":
                    cle = (duree, arrivee, nom)
                else:
                    cle = (priorite, arrivee, nom)
                if meilleure_cle is None or cle < meilleure_cle:
                    choix = processus
                    meilleure_cle = cle

        if choix is None:
            prochaine_arrivee = a_faire[0][0]
            gantt.append(("IDLE", horloge, prochaine_arrivee))
            horloge = prochaine_arrivee
        else:
            arrivee, nom, duree, priorite = choix
            fin = horloge + duree
            gantt.append((nom, horloge, fin))
            horloge = fin
            a_faire.remove(choix)

    return gantt


def round_robin(ordre, quantum):
    """Execute Round Robin et place les nouvelles arrivees avant reinsertion."""
    gantt = []
    file = []
    restant = {}
    suivant = 0
    horloge = 0

    for arrivee, nom, duree, priorite in ordre:
        restant[nom] = duree

    while suivant < len(ordre) or file:
        if not file:
            arrivee = ordre[suivant][0]
            if arrivee > horloge:
                gantt.append(("IDLE", horloge, arrivee))
                horloge = arrivee
            while suivant < len(ordre) and ordre[suivant][0] <= horloge:
                file.append(ordre[suivant][1])
                suivant += 1

        nom = file.pop(0)
        duree = min(quantum, restant[nom])
        fin = horloge + duree
        gantt.append((nom, horloge, fin))
        horloge = fin
        restant[nom] -= duree

        # A la fin d'une tranche, les nouveaux arrivent avant le processus
        # interrompu. Cette convention rend le Gantt reproductible.
        while suivant < len(ordre) and ordre[suivant][0] <= horloge:
            file.append(ordre[suivant][1])
            suivant += 1
        if restant[nom] > 0:
            file.append(nom)

    return gantt


def ordonnancer(processus, algorithme, quantum=2):
    """Valide puis simule fcfs, sjf, priorite ou rr.

    Chaque dictionnaire doit etre exactement de la forme suivante :
    {"nom": str, "arrivee": int, "duree": int, "priorite": int}.
    Le resultat est (gantt, lignes). Les lignes gardent l'ordre des entrees.
    """
    if not isinstance(processus, list) or not processus:
        raise ValueError("Ajoute une liste non vide de processus.")
    if not isinstance(algorithme, str):
        raise ValueError("L'algorithme doit etre un texte.")

    ordre = []
    noms = []
    for processus_un in processus:
        if not isinstance(processus_un, dict):
            raise ValueError("Chaque processus doit etre un dictionnaire.")
        if len(processus_un) != 4:
            raise ValueError(
                "Chaque processus exige nom, arrivee, duree et priorite."
            )
        if "nom" not in processus_un or "arrivee" not in processus_un:
            raise ValueError(
                "Chaque processus exige nom, arrivee, duree et priorite."
            )
        if "duree" not in processus_un or "priorite" not in processus_un:
            raise ValueError(
                "Chaque processus exige nom, arrivee, duree et priorite."
            )

        nom = processus_un["nom"]
        arrivee = processus_un["arrivee"]
        duree = processus_un["duree"]
        priorite = processus_un["priorite"]
        if not isinstance(nom, str) or not nom.strip():
            raise ValueError("Le nom doit etre un texte non vide.")
        if nom.upper() == "IDLE" or nom in noms:
            raise ValueError("Les noms doivent etre uniques et differents de IDLE.")
        if not isinstance(arrivee, int) or isinstance(arrivee, bool):
            raise ValueError("L'arrivee doit etre un entier.")
        if not isinstance(duree, int) or isinstance(duree, bool):
            raise ValueError("La duree doit etre un entier.")
        if not isinstance(priorite, int) or isinstance(priorite, bool):
            raise ValueError("La priorite doit etre un entier.")
        if arrivee < 0 or duree <= 0:
            raise ValueError("L'arrivee doit etre >= 0 et la duree doit etre > 0.")

        noms.append(nom)
        ordre.append((arrivee, nom, duree, priorite))

    algorithme = algorithme.lower().strip().replace("_", "-")
    if algorithme == "priority":
        algorithme = "priorite"
    if algorithme == "round-robin" or algorithme == "roundrobin":
        algorithme = "rr"
    if algorithme not in ("fcfs", "sjf", "priorite", "rr"):
        raise ValueError("Choisis fcfs, sjf, rr, priorite ou priority.")
    if algorithme == "rr":
        if not isinstance(quantum, int) or isinstance(quantum, bool):
            raise ValueError("Le quantum doit etre un entier.")
        if quantum <= 0:
            raise ValueError("Le quantum doit etre strictement positif.")

    # Le tri compare d'abord l'arrivee, puis le nom en cas d'egalite.
    ordre.sort()
    if algorithme == "fcfs":
        gantt = fcfs(ordre)
    elif algorithme == "sjf" or algorithme == "priorite":
        gantt = sjf_ou_priorite(ordre, algorithme)
    else:
        gantt = round_robin(ordre, quantum)

    fins = {}
    for nom, debut, fin in gantt:
        if nom != "IDLE":
            fins[nom] = fin

    lignes = []
    for processus_un in processus:
        nom = processus_un["nom"]
        arrivee = processus_un["arrivee"]
        duree = processus_un["duree"]
        priorite = processus_un["priorite"]
        fin = fins[nom]
        sejour = fin - arrivee
        attente = sejour - duree
        lignes.append((nom, arrivee, duree, priorite, fin, attente, sejour))

    return gantt, lignes
