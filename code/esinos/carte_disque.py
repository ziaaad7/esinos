"""Cartes et suivi pédagogiques d'une image disque ESINOS, en lecture seule."""

import base64

from .filesystem import charger, chercher_inode, format_disque
from .disque_binaire import geometrie

def carte_physique(disque):
    geo = geometrie(disque)
    zones = (
        ("S", "Superbloc", 0, geo["blocs_superbloc"]),
        ("B", "Bitmap", geo["bloc_bitmap"], geo["blocs_bitmap"]),
        ("I", "Inodes", geo["bloc_inodes"], geo["blocs_inodes"]),
        ("R", "Répertoire", geo["bloc_repertoire"], geo["blocs_repertoire"]),
    )
    total = geo["nombre_blocs_physiques"]
    symboles = ["?"] * total
    lignes = ["STRUCTURE PHYSIQUE DU DISQUE BINAIRE"]
    for symbole, nom, debut, nombre in zones:
        lignes.append(f"{symbole} {nom} : blocs {debut} à {debut + nombre - 1}")
        for numero in range(debut, debut + nombre):
            symboles[numero] = symbole
    for numero, bloc in enumerate(disque["blocs"]):
        symboles[geo["data_start"] + numero] = "#" if bloc is not None else "."
    lignes.append(f"Données : blocs {geo['data_start']} à {total - 1}")
    lignes.append(f"Image : {geo['taille_image']} octets, {total} blocs physiques.")
    if total <= 256:
        for debut in range(0, total, 16):
            fin = min(debut + 16, total)
            lignes.append(f"physique {debut}-{fin - 1} : {''.join(symboles[debut:fin])}")
    else:
        lignes.append("La carte physique est condensée dans les zones ci-dessus.")
    lignes.append(f"Bloc de données logique 0 -> bloc physique {geo['data_start']}.")
    return "\n".join(lignes)

def carte_blocs(chemin):
    disque = charger(chemin)
    blocs = disque["blocs"]
    lignes = [carte_physique(disque)] if format_disque(chemin) == "binaire" else []
    lignes += [
        "CARTE DES BLOCS DE DONNÉES (NUMÉROS LOGIQUES)",
        "Legende : # occupe | . libre",
        "Chaque caractere represente un bloc numerote.",
    ]
    etats = []
    for bloc in blocs:
        etats.append("." if bloc is None else "#")
    for debut in range(0, len(blocs), 16):
        fin = min(debut + 16, len(blocs))
        lignes.append(f"{debut}-{fin - 1} : {''.join(etats[debut:fin])}")

    lignes.append("Inodes et blocs :")
    occupe = False
    for inode in disque["inodes"]:
        if inode is not None:
            occupe = True
            numeros = ", ".join(map(str, inode["blocs"])) or "aucun"
            lignes.append(f"inode {inode['numero']} ({inode['nom']}) -> blocs {numeros}")
    if not occupe:
        lignes.append("aucun inode occupe")
    return "\n".join(lignes)

def explication_fichier(chemin, nom):
    disque = charger(chemin)
    inode = chercher_inode(disque, nom)
    if inode is None:
        raise ValueError("Fichier introuvable : " + str(nom))

    taille_bloc = disque["taille_bloc"]
    morceaux = []
    for numero in inode["blocs"]:
        morceaux.append(base64.b64decode(disque["blocs"][numero].encode("ascii")))
    contenu = b"".join(morceaux).decode("utf-8")
    taille = inode["taille"]
    lignes = ["FICHIER : " + inode["nom"], "Inode : " + str(inode["numero"]),
              "Taille : " + str(taille) + " octets",
              "Capacite d'un bloc : " + str(taille_bloc) + " octets",
              "Nombre de blocs : " + str((taille + taille_bloc - 1) // taille_bloc),
              "Contenu UTF-8 assemble : " + contenu]
    if format_disque(chemin) == "binaire":
        data_start = geometrie(disque)["data_start"]
        for numero in inode["blocs"]:
            physique = data_start + numero
            lignes.append(
                f"Logique {numero} -> physique {physique}, position "
                f"{physique * taille_bloc} octets dans l'image."
            )

    if not morceaux:
        lignes.append("Aucun bloc : fichier vide.")
        lignes.append("Capacite inutilisee du dernier bloc : 0 octet.")
    else:
        for numero, morceau in zip(inode["blocs"], morceaux):
            lignes.append(f"Bloc {numero} : {len(morceau)}/{taille_bloc} octets occupes")
        lignes.append(
            "Capacite inutilisee du dernier bloc : "
            f"{taille_bloc - len(morceaux[-1])} octets."
        )
    return "\n".join(lignes)
