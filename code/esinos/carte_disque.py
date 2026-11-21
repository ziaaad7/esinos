"""Affichages pedagogiques pour l'image disque JSON d'ESINOS.

Ce module lit seulement l'image par les fonctions publiques du systeme de
fichiers. Il ne reserve aucun bloc supplementaire et ne modifie jamais le JSON.
"""

import base64

from .filesystem import charger, chercher_inode, format_disque
from .disque_binaire import geometrie


def carte_physique(disque):
    """Montre les zones réservées et leur position avant les données."""
    geo = geometrie(disque)
    zones = [
        ("S", "Superbloc", 0, geo["blocs_superbloc"]),
        ("B", "Bitmap", geo["bloc_bitmap"], geo["blocs_bitmap"]),
        ("I", "Inodes", geo["bloc_inodes"], geo["blocs_inodes"]),
        ("R", "Répertoire", geo["bloc_repertoire"], geo["blocs_repertoire"]),
    ]
    lignes = ["STRUCTURE PHYSIQUE DU DISQUE BINAIRE"]
    for symbole, nom, debut, nombre in zones:
        lignes.append(f"{symbole} {nom} : blocs {debut} à {debut + nombre - 1}")
    lignes.append(f"Données : blocs {geo['data_start']} à "
                  f"{geo['nombre_blocs_physiques'] - 1}")
    lignes.append(f"Image : {geo['taille_image']} octets, "
                  f"{geo['nombre_blocs_physiques']} blocs physiques.")
    if geo["nombre_blocs_physiques"] <= 256:
        debut = 0
        while debut < geo["nombre_blocs_physiques"]:
            fin = min(debut + 16, geo["nombre_blocs_physiques"])
            cases = ""
            for numero in range(debut, fin):
                symbole = "."
                if numero >= geo["data_start"]:
                    if disque["blocs"][numero - geo["data_start"]] is not None:
                        symbole = "#"
                else:
                    for lettre, nom, premiere, nombre in zones:
                        if premiere <= numero < premiere + nombre:
                            symbole = lettre
                            break
                cases += symbole
            lignes.append(f"physique {debut}-{fin - 1} : {cases}")
            debut = fin
    else:
        lignes.append("La carte physique est condensée dans les zones ci-dessus.")
    lignes.append(f"Bloc de données logique 0 -> bloc physique {geo['data_start']}.")
    return "\n".join(lignes)


def carte_blocs(chemin):
    """Retourne une carte texte de tous les blocs et de leurs proprietaires."""
    disque = charger(chemin)
    blocs = disque["blocs"]
    inodes = disque["inodes"]
    lignes = []

    if format_disque(chemin) == "binaire":
        lignes.append(carte_physique(disque))

    lignes.append("CARTE DES BLOCS DE DONNÉES (NUMÉROS LOGIQUES)")
    lignes.append("Legende : # occupe | . libre")
    lignes.append("Chaque caractere represente un bloc numerote.")

    debut = 0
    while debut < len(blocs):
        fin = min(debut + 16, len(blocs))
        etat = ""
        for numero in range(debut, fin):
            if blocs[numero] is None:
                etat = etat + "."
            else:
                etat = etat + "#"
        lignes.append(str(debut) + "-" + str(fin - 1) + " : " + etat)
        debut = fin

    lignes.append("Inodes et blocs :")
    trouve = False
    for inode in inodes:
        if inode is not None:
            trouve = True
            numeros = ""
            for position in range(len(inode["blocs"])):
                if position > 0:
                    numeros = numeros + ", "
                numeros = numeros + str(inode["blocs"][position])
            if numeros == "":
                numeros = "aucun"
            lignes.append(
                "inode " + str(inode["numero"]) + " (" + inode["nom"]
                + ") -> blocs " + numeros
            )
    if not trouve:
        lignes.append("aucun inode occupe")

    return "\n".join(lignes)


def explication_fichier(chemin, nom):
    """Retourne une explication texte de l'inode, des blocs et du contenu."""
    disque = charger(chemin)
    inode = chercher_inode(disque, nom)
    if inode is None:
        raise ValueError("Fichier introuvable : " + str(nom))

    taille_bloc = disque["taille_bloc"]
    taille = inode["taille"]
    nombre_blocs = (taille + taille_bloc - 1) // taille_bloc
    contenu = b""
    tailles_blocs = []

    for numero_bloc in inode["blocs"]:
        morceau = base64.b64decode(disque["blocs"][numero_bloc].encode("ascii"))
        contenu = contenu + morceau
        tailles_blocs.append(len(morceau))

    texte = contenu.decode("utf-8")
    lignes = []
    lignes.append("FICHIER : " + inode["nom"])
    lignes.append("Inode : " + str(inode["numero"]))
    lignes.append("Taille : " + str(taille) + " octets")
    lignes.append("Capacite d'un bloc : " + str(taille_bloc) + " octets")
    lignes.append("Nombre de blocs : " + str(nombre_blocs))
    lignes.append("Contenu UTF-8 assemble : " + texte)

    if format_disque(chemin) == "binaire":
        geo = geometrie(disque)
        for numero_bloc in inode["blocs"]:
            physique = geo["data_start"] + numero_bloc
            position = physique * taille_bloc
            lignes.append(f"Logique {numero_bloc} -> physique {physique}, "
                          f"position {position} octets dans l'image.")

    if nombre_blocs == 0:
        lignes.append("Aucun bloc : fichier vide.")
        lignes.append("Capacite inutilisee du dernier bloc : 0 octet.")
    else:
        for position in range(nombre_blocs):
            lignes.append(
                "Bloc " + str(inode["blocs"][position]) + " : "
                + str(tailles_blocs[position]) + "/" + str(taille_bloc)
                + " octets occupes"
            )
        inutilisee = taille_bloc - tailles_blocs[-1]
        lignes.append(
            "Capacite inutilisee du dernier bloc : " + str(inutilisee)
            + " octets."
        )

    return "\n".join(lignes)
