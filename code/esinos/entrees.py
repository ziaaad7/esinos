"""Lecture et validation des saisies du Terminal."""
from math import isfinite


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
