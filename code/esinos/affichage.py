"""Affichage texte et explications pas à pas du processeur."""

from .scheduler import ordonnancer

def _est_entier(valeur):
    return isinstance(valeur, int) and not isinstance(valeur, bool)


def _verifier_gantt(gantt):
    if not isinstance(gantt, (list, tuple)):
        raise ValueError("Le Gantt doit être une liste de tranches.")
    resultat = []
    fin_precedente = None
    for tranche in gantt:
        if not isinstance(tranche, (list, tuple)) or len(tranche) != 3:
            raise ValueError("Une tranche doit être (nom, debut, fin).")
        nom, debut, fin = tranche
        if not isinstance(nom, str) or not nom:
            raise ValueError("Le nom d'une tranche doit être un texte.")
        if not _est_entier(debut) or not _est_entier(fin):
            raise ValueError("Les bornes du Gantt doivent être des entiers.")
        if fin <= debut:
            raise ValueError("Une tranche doit avoir une durée positive.")
        if fin_precedente is not None and debut != fin_precedente:
            raise ValueError("Les tranches du Gantt doivent être contiguës.")
        resultat.append((nom, debut, fin))
        fin_precedente = fin
    return resultat

def _noms(elements):
    noms = []
    for element in elements:
        noms.append(element if isinstance(element, str) else element[1])
    return ", ".join(noms) if noms else "aucun"

def _bordure(largeurs):
    morceaux = []
    for largeur in largeurs:
        morceaux.append("-" * (largeur + 2))
    return "+" + "+".join(morceaux) + "+"

def _ligne(valeurs, largeurs, droite=None):
    cellules = []
    for index in range(len(valeurs)):
        valeur = valeurs[index]
        if droite is not None and droite[index]:
            valeur = valeur.rjust(largeurs[index])
        else:
            valeur = valeur.ljust(largeurs[index])
        cellules.append(f" {valeur} ")
    return "|" + "|".join(cellules) + "|"

def gantt_texte(gantt, largeur=90):
    """Renvoie un Gantt encadré, à largeur de case fixe."""
    if not _est_entier(largeur) or largeur < 20:
        raise ValueError("La largeur doit être un entier d'au moins 20.")
    segments = _verifier_gantt(gantt)
    if not segments:
        return "GANTT : vide"
    largeur_case = 12
    for nom, debut, fin in segments:
        largeur_case = max(largeur_case, len(f"{debut} -> {fin}"))
    colonnes = max(1, (largeur - 1) // (largeur_case + 3))
    lignes = ["GANTT", "Cases de largeur fixe; bornes = durées exactes."]
    depart = 0
    while depart < len(segments):
        partie = segments[depart:depart + colonnes]
        depart += len(partie)
        noms = []
        bornes = []
        for nom, debut, fin in partie:
            if len(nom) > largeur_case:
                nom = nom[:largeur_case - 3] + "..."
            noms.append(nom)
            bornes.append(f"{debut} -> {fin}")
        largeurs = [largeur_case] * len(partie)
        bordure = _bordure(largeurs)
        lignes.append(bordure)
        lignes.append(_ligne(noms, largeurs))
        lignes.append(_ligne(bornes, largeurs))
        lignes.append(bordure)
    for nom, debut, fin in segments:
        if nom == "IDLE":
            lignes.append("IDLE = CPU libre entre deux arrivées.")
            break
    return "\n".join(lignes)

def tableau_texte(entetes, lignes):
    """Renvoie un tableau ASCII, avec nombres alignés à droite."""
    if not isinstance(entetes, (list, tuple)) or not entetes:
        raise ValueError("Le tableau doit avoir au moins un en-tête.")
    if not isinstance(lignes, (list, tuple)):
        raise ValueError("Les lignes doivent être une liste ou un tuple.")
    textes_entetes = []
    largeurs = []
    nombres = [True] * len(entetes)
    for entete in entetes:
        texte = "-" if entete is None else str(entete)
        textes_entetes.append(texte)
        largeurs.append(len(texte))
    textes_lignes = []
    for ligne in lignes:
        if not isinstance(ligne, (list, tuple)):
            raise ValueError("Chaque ligne doit être une liste ou un tuple.")
        if len(ligne) != len(entetes):
            raise ValueError("Chaque ligne doit avoir autant de valeurs que les en-têtes.")
        textes = []
        for index in range(len(ligne)):
            valeur = ligne[index]
            texte = "-" if valeur is None else str(valeur)
            textes.append(texte)
            largeurs[index] = max(largeurs[index], len(texte))
            if (valeur is None or not isinstance(valeur, (int, float))
                    or isinstance(valeur, bool)):
                nombres[index] = False
        textes_lignes.append(textes)
    bordure = _bordure(largeurs)
    resultat = [bordure, _ligne(textes_entetes, largeurs), bordure]
    for ligne in textes_lignes:
        resultat.append(_ligne(ligne, largeurs, nombres))
    resultat.append(bordure)
    return "\n".join(resultat)

def _expliquer_sans_preemption(ordre, segments, algorithme):
    restant = list(ordre)
    explications = []
    for nom, debut, fin in segments:
        if nom == "IDLE":
            prochain = restant[0]
            explications.append(
                f"t={debut} -> {fin} : IDLE, aucun processus n'est prêt. "
                f"{prochain[1]} arrive à t={prochain[0]}."
            )
            continue
        choisi = None
        prets = []
        for processus in restant:
            if processus[0] <= debut:
                prets.append(processus)
            if processus[1] == nom:
                choisi = processus
        if choisi is None:
            raise ValueError("Le Gantt contient un processus inconnu.")
        arrivee, nom, duree, priorite = choisi
        prets_texte = _noms(prets)
        if algorithme == "fcfs":
            texte = f"FCFS choisit {nom}, arrivé le premier parmi {prets_texte}."
        elif algorithme == "sjf":
            texte = f"SJF choisit {nom} (durée {duree}), la plus courte parmi {prets_texte}."
        else:
            texte = (f"Priority choisit {nom} (priorité {priorite}, chiffre le plus "
                     f"petit) parmi {prets_texte}.")
        explications.append(f"t={debut} : {texte} Tranche {debut} -> {fin}.")
        restant.remove(choisi)
    return explications

def _expliquer_rr(ordre, segments):
    restant = {}
    for arrivee, nom, duree, priorite in ordre:
        restant[nom] = duree
    file = []
    suivant = 0
    explications = []
    for nom, debut, fin in segments:
        while suivant < len(ordre) and ordre[suivant][0] <= debut:
            file.append(ordre[suivant])
            suivant += 1
        if nom == "IDLE":
            if file:
                raise ValueError("Le Gantt ne suit pas la file Round Robin.")
            explications.append(
                f"t={debut} -> {fin} : IDLE, aucun processus n'est prêt."
            )
            continue
        file_avant = _noms(file)
        if not file or file[0][1] != nom:
            raise ValueError("Le Gantt ne suit pas la file Round Robin.")
        courant = file.pop(0)
        duree = fin - debut
        reste_avant = restant[nom]
        restant[nom] -= duree
        arrives = []
        while suivant < len(ordre) and ordre[suivant][0] <= fin:
            nouveau = ordre[suivant]
            file.append(nouveau)
            arrives.append(nouveau)
            suivant += 1
        if restant[nom] > 0:
            file.append(courant)
        texte = (f"t={debut} : Round Robin donne {duree} unité(s) à {nom} "
                 f"(reste {reste_avant} -> {restant[nom]}). "
                 f"File avant : {file_avant}. ")
        if arrives:
            texte += f"Arrivées pendant la tranche : {_noms(arrives)}. "
        else:
            texte += "Aucune arrivée pendant la tranche. "
        explications.append(f"{texte}File suivante : {_noms(file)}.")
    return explications

def explication_cpu(processus, gantt, algorithme, quantum=2):
    """Explique chaque tranche seulement si elle correspond au calcul."""
    segments = _verifier_gantt(gantt)
    if not segments:
        raise ValueError("Le Gantt ne peut pas être vide pour ces processus.")
    attendu, _ = ordonnancer(processus, algorithme, quantum)
    if segments != attendu:
        raise ValueError("Le Gantt fourni ne correspond pas à la simulation.")
    ordre = []
    for processus_un in processus:
        ordre.append((processus_un["arrivee"], processus_un["nom"],
                      processus_un["duree"], processus_un["priorite"]))
    ordre.sort()
    nom = algorithme.lower().strip().replace("_", "-")
    if nom == "priority":
        nom = "priorite"
    if nom == "round-robin" or nom == "roundrobin":
        nom = "rr"
    if nom == "rr":
        return _expliquer_rr(ordre, segments)
    return _expliquer_sans_preemption(ordre, segments, nom)
