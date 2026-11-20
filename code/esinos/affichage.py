"""Affichage texte et explications du CPU pour ESINOS.

Les fonctions de ce module ne font aucun print. Elles reçoivent des listes et
des dictionnaires puis renvoient du texte ou une liste de phrases.
"""

from .scheduler import ordonnancer


def _est_entier(valeur):
    """True pour un entier, mais pas pour True ou False."""
    return isinstance(valeur, int) and not isinstance(valeur, bool)


def _verifier_gantt(gantt):
    """Copie et vérifie des tranches (nom, debut, fin) contiguës."""
    if not isinstance(gantt, (list, tuple)):
        raise ValueError("Le Gantt doit être une liste de tranches.")

    segments = []
    fin_precedente = None
    for tranche in gantt:
        if not isinstance(tranche, (list, tuple)) or len(tranche) != 3:
            raise ValueError("Une tranche doit être (nom, debut, fin).")

        nom, debut, fin = tranche
        if not isinstance(nom, str) or nom == "":
            raise ValueError("Le nom d'une tranche doit être un texte.")
        if not _est_entier(debut) or not _est_entier(fin):
            raise ValueError("Les bornes du Gantt doivent être des entiers.")
        if fin <= debut:
            raise ValueError("Une tranche doit avoir une durée positive.")
        if fin_precedente is not None and debut != fin_precedente:
            raise ValueError("Les tranches du Gantt doivent être contiguës.")

        segments.append((nom, debut, fin))
        fin_precedente = fin

    return segments


def _couper_texte(texte, largeur):
    """Abrège un nom trop long sans étirer le dessin."""
    if len(texte) <= largeur:
        return texte
    if largeur <= 3:
        return texte[:largeur]
    return texte[:largeur - 3] + "..."


def _bordure(nombre_cases, largeur_case):
    """Construit le haut ou le bas d'une rangée du Gantt."""
    texte = "+"
    for numero in range(nombre_cases):
        texte = texte + "-" * (largeur_case + 2) + "+"
    return texte


def _ligne_cases(valeurs, largeur_case):
    """Place plusieurs valeurs dans des cases de même largeur."""
    texte = "|"
    for valeur in valeurs:
        texte = texte + " " + valeur.ljust(largeur_case) + " |"
    return texte


def gantt_texte(gantt, largeur=90):
    """Renvoie un Gantt encadré.

    Chaque case contient un nom et ses bornes exactes. Sa largeur ne dépend pas
    de la durée simulée. Un processus qui dure un million d'unités ne crée donc
    pas un million de caractères. Les noms longs sont abrégés avec trois points.
    """
    if not _est_entier(largeur) or largeur < 20:
        raise ValueError("La largeur doit être un entier d'au moins 20.")

    segments = _verifier_gantt(gantt)
    if len(segments) == 0:
        return "GANTT : vide"

    largeur_case = 12
    for nom, debut, fin in segments:
        bornes = str(debut) + " -> " + str(fin)
        if len(bornes) > largeur_case:
            largeur_case = len(bornes)

    colonnes = (largeur - 1) // (largeur_case + 3)
    if colonnes < 1:
        colonnes = 1

    lignes = ["GANTT", "Cases de largeur fixe; bornes = durées exactes."]
    index = 0
    while index < len(segments):
        partie = []
        while len(partie) < colonnes and index < len(segments):
            partie.append(segments[index])
            index += 1

        noms = []
        bornes = []
        for nom, debut, fin in partie:
            noms.append(_couper_texte(nom, largeur_case))
            bornes.append(str(debut) + " -> " + str(fin))

        bordure = _bordure(len(partie), largeur_case)
        lignes.append(bordure)
        lignes.append(_ligne_cases(noms, largeur_case))
        lignes.append(_ligne_cases(bornes, largeur_case))
        lignes.append(bordure)

    for nom, debut, fin in segments:
        if nom == "IDLE":
            lignes.append("IDLE = CPU libre entre deux arrivées.")
            break

    texte = ""
    for index in range(len(lignes)):
        if index > 0:
            texte = texte + "\n"
        texte = texte + lignes[index]
    return texte


def _texte_valeur(valeur):
    """Transforme None en tiret pour les tableaux."""
    if valeur is None:
        return "-"
    return str(valeur)


def _bordure_tableau(largeurs):
    texte = "+"
    for largeur in largeurs:
        texte = texte + "-" * (largeur + 2) + "+"
    return texte


def _ligne_tableau(valeurs, largeurs, nombres):
    texte = "|"
    for index in range(len(valeurs)):
        valeur = valeurs[index]
        largeur = largeurs[index]
        if nombres[index]:
            valeur = valeur.rjust(largeur)
        else:
            valeur = valeur.ljust(largeur)
        texte = texte + " " + valeur + " |"
    return texte


def tableau_texte(entetes, lignes):
    """Renvoie un tableau ASCII avec colonnes alignées.

    entetes et chaque ligne sont des listes ou tuples de même longueur. None
    est affiché sous la forme d'un tiret.
    """
    if not isinstance(entetes, (list, tuple)) or len(entetes) == 0:
        raise ValueError("Le tableau doit avoir au moins un en-tête.")
    if not isinstance(lignes, (list, tuple)):
        raise ValueError("Les lignes doivent être une liste ou un tuple.")

    entetes_texte = []
    largeurs = []
    nombres = []
    for entete in entetes:
        texte = _texte_valeur(entete)
        entetes_texte.append(texte)
        largeurs.append(len(texte))
        nombres.append(True)

    lignes_texte = []
    for ligne in lignes:
        if not isinstance(ligne, (list, tuple)):
            raise ValueError("Chaque ligne doit être une liste ou un tuple.")
        if len(ligne) != len(entetes):
            raise ValueError(
                "Chaque ligne doit avoir autant de valeurs que les en-têtes."
            )

        ligne_texte = []
        for index in range(len(ligne)):
            valeur = ligne[index]
            texte = _texte_valeur(valeur)
            ligne_texte.append(texte)
            if len(texte) > largeurs[index]:
                largeurs[index] = len(texte)
            if valeur is None:
                nombres[index] = False
            elif not isinstance(valeur, (int, float)):
                nombres[index] = False
            elif isinstance(valeur, bool):
                nombres[index] = False
        lignes_texte.append(ligne_texte)

    bordure = _bordure_tableau(largeurs)
    resultat = [bordure]
    resultat.append(_ligne_tableau(entetes_texte, largeurs, [False] * len(entetes)))
    resultat.append(bordure)
    for ligne in lignes_texte:
        resultat.append(_ligne_tableau(ligne, largeurs, nombres))
    resultat.append(bordure)

    texte = ""
    for index in range(len(resultat)):
        if index > 0:
            texte = texte + "\n"
        texte = texte + resultat[index]
    return texte


def _ordre_processus(processus):
    """Reconstruit seulement l'ordre déjà validé par ordonnancer."""
    ordre = []
    for processus_un in processus:
        valeur = (
            processus_un["arrivee"], processus_un["nom"],
            processus_un["duree"], processus_un["priorite"],
        )
        ordre.append(valeur)
    ordre.sort()
    return ordre


def _nom_algorithme(algorithme):
    """Obtient le nom interne après la validation faite par ordonnancer."""
    nom = algorithme.lower().strip().replace("_", "-")
    if nom == "priority":
        return "priorite"
    if nom == "round-robin" or nom == "roundrobin":
        return "rr"
    return nom


def _texte_noms(processus):
    """Transforme une liste de processus en une liste de noms lisible."""
    if len(processus) == 0:
        return "aucun"

    texte = ""
    for index in range(len(processus)):
        element = processus[index]
        if isinstance(element, str):
            nom = element
        else:
            nom = element[1]
        if index > 0:
            texte = texte + ", "
        texte = texte + nom
    return texte


def _explication_sans_preemption(ordre, segments, algorithme):
    """Explique les tranches validées de FCFS, SJF ou Priority."""
    a_faire = list(ordre)
    explications = []
    temps = 0
    index = 0

    while len(a_faire) > 0:
        nom, debut, fin = segments[index]

        if nom == "IDLE":
            prochain = a_faire[0]
            explications.append(
                f"t={debut} -> {fin} : IDLE, aucun processus n'est prêt. "
                f"{prochain[1]} arrive à t={prochain[0]}."
            )
            temps = fin
            index += 1
            continue

        choisi = None
        for processus_un in a_faire:
            if processus_un[1] == nom:
                choisi = processus_un
                break
        if choisi is None:
            raise ValueError("Le Gantt contient un processus inconnu.")

        prets = []
        for processus_un in a_faire:
            if processus_un[0] <= temps:
                prets.append(processus_un)
        prets_texte = _texte_noms(prets)
        arrivee, nom, duree, priorite = choisi

        if algorithme == "fcfs":
            phrase = (
                f"t={temps} : FCFS choisit {nom}, arrivé le premier parmi "
                f"{prets_texte}. "
            )
        elif algorithme == "sjf":
            phrase = (
                f"t={temps} : SJF choisit {nom} (durée {duree}), "
                f"la plus courte parmi {prets_texte}. "
            )
        else:
            phrase = (
                f"t={temps} : Priority choisit {nom} (priorité {priorite}, "
                f"chiffre le plus petit) parmi {prets_texte}. "
            )
        explications.append(f"{phrase}Tranche {debut} -> {fin}.")

        temps = fin
        index += 1
        a_faire.remove(choisi)

    if index != len(segments):
        raise ValueError("Le Gantt contient une tranche CPU inattendue.")
    return explications


def _explication_rr(ordre, segments, quantum):
    """Explique les tranches Round Robin validées et l'état de la file."""
    restant = {}
    for arrivee, nom, duree, priorite in ordre:
        restant[nom] = duree

    a_venir = list(ordre)
    file = []
    explications = []
    temps = 0
    suivant = 0
    index = 0

    while suivant < len(a_venir) or len(file) > 0:
        if len(file) == 0:
            prochaine_arrivee = a_venir[suivant][0]
            if temps < prochaine_arrivee:
                nom, debut, fin = segments[index]
                explications.append(
                    f"t={debut} -> {fin} : IDLE, aucun processus n'est prêt."
                )
                temps = fin
                index += 1

            while suivant < len(a_venir):
                processus_un = a_venir[suivant]
                if processus_un[0] > temps:
                    break
                file.append(processus_un)
                suivant += 1

        file_avant = _texte_noms(file)
        courant = file.pop(0)
        arrivee, nom_courant, duree_totale, priorite = courant
        reste_avant = restant[nom_courant]

        nom, debut, fin = segments[index]
        if nom != nom_courant:
            raise ValueError("Le Gantt ne suit pas la file Round Robin.")
        duree = fin - debut
        restant[nom] = reste_avant - duree
        temps = fin
        index += 1

        arrives = []
        while suivant < len(a_venir):
            processus_un = a_venir[suivant]
            if processus_un[0] > temps:
                break
            file.append(processus_un)
            arrives.append(processus_un)
            suivant += 1

        if restant[nom] > 0:
            file.append(courant)

        phrase = (
            f"t={debut} : Round Robin donne {duree} unité(s) à {nom} "
            f"(reste {reste_avant} -> {restant[nom]}). "
            f"File avant : {file_avant}. "
        )
        if len(arrives) > 0:
            phrase = f"{phrase}Arrivées pendant la tranche : "
            phrase = f"{phrase}{_texte_noms(arrives)}. "
        else:
            phrase = f"{phrase}Aucune arrivée pendant la tranche. "
        explications.append(f"{phrase}File suivante : {_texte_noms(file)}.")

    if index != len(segments):
        raise ValueError("Le Gantt contient une tranche CPU inattendue.")
    return explications


def explication_cpu(processus, gantt, algorithme, quantum=2):
    """Renvoie une explication fiable, une phrase par tranche du Gantt.

    ordonnancer valide les entrées et recalcule le Gantt attendu. Le Gantt
    fourni n'est jamais remplacé. S'il est différent, ValueError est levée
    plutôt que d'inventer une explication.
    """
    segments = _verifier_gantt(gantt)
    if len(segments) == 0:
        raise ValueError("Le Gantt ne peut pas être vide pour ces processus.")

    gantt_attendu, _ = ordonnancer(processus, algorithme, quantum)
    if segments != gantt_attendu:
        raise ValueError("Le Gantt fourni ne correspond pas à la simulation.")

    ordre = _ordre_processus(processus)
    algorithme = _nom_algorithme(algorithme)
    if algorithme == "rr":
        return _explication_rr(ordre, segments, quantum)
    return _explication_sans_preemption(ordre, segments, algorithme)
