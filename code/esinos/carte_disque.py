"""Affichages pedagogiques pour l'image disque JSON d'ESINOS.

Ce module lit seulement l'image par les fonctions publiques du systeme de
fichiers. Il ne reserve aucun bloc supplementaire et ne modifie jamais le JSON.
"""

import base64

from .filesystem import charger, chercher_inode


def carte_blocs(chemin):
    """Retourne une carte texte de tous les blocs et de leurs proprietaires."""
    disque = charger(chemin)
    blocs = disque["blocs"]
    inodes = disque["inodes"]
    lignes = []

    lignes.append("CARTE DES BLOCS")
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
