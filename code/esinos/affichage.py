"""Construction des Gantt et tableaux texte."""

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
