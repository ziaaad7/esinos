"""Mini disque ESINOS, ecrit avec des fonctions, listes et dictionnaires.

Le programme manipule une image interne tres simple : les noms des cles sont
en francais et les inodes occupent directement une case de la liste. Au moment
de sauvegarder, cette image est traduite vers le format JSON canonique du
projet ESINOS (schema version 1, blocs Base64). Ainsi, l'atelier peut ouvrir
une ancienne image francaise en hexadecimal et une image creee par le projet
publie, puis les sauvegarder dans un format compatible.
"""

import base64
import binascii
import errno
import json
import os
import re
import tempfile


SCHEMA = "esinos-mini-filesystem"
VERSION = 1
NOM_SIMPLE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def _verifier_entier_positif(valeur, etiquette):
    """Vérifie qu'une taille est un entier strictement positif."""
    if isinstance(valeur, bool) or not isinstance(valeur, int):
        raise ValueError(etiquette + " doit etre un entier.")
    if valeur <= 0:
        raise ValueError(etiquette + " doit etre strictement positif.")


def _verifier_nom(nom):
    """Applique les memes limites de nom que le projet publie."""
    if not isinstance(nom, str) or NOM_SIMPLE.fullmatch(nom) is None:
        raise ValueError(
            "Nom invalide : utilise 1 a 64 lettres, chiffres, points, _ ou -."
        )


def _encoder_bloc(octets):
    """Transforme des octets en texte Base64 pour pouvoir les mettre en JSON."""
    return base64.b64encode(octets).decode("ascii")


def _decoder_bloc(texte):
    """Relit un bloc Base64 et produit une erreur lisible si le JSON est faux."""
    if not isinstance(texte, str) or texte == "":
        raise ValueError("Un bloc occupe doit contenir du texte Base64 non vide.")
    try:
        return base64.b64decode(texte.encode("ascii"), validate=True)
    except (UnicodeEncodeError, ValueError, binascii.Error):
        raise ValueError("Un bloc de l'image n'est pas du Base64 valide.")


def _verifier_image(disque):
    """Verifie les liens entre table d'inodes, blocs et contenu texte."""
    if not isinstance(disque, dict):
        raise ValueError("Le disque doit etre un dictionnaire.")
    if "taille_bloc" not in disque or "blocs" not in disque:
        raise ValueError("Il manque la taille ou les blocs du disque.")
    if "inodes" not in disque:
        raise ValueError("Il manque la table d'inodes du disque.")

    taille_bloc = disque["taille_bloc"]
    blocs = disque["blocs"]
    inodes = disque["inodes"]
    _verifier_entier_positif(taille_bloc, "La taille de bloc")
    if not isinstance(blocs, list) or not blocs:
        raise ValueError("La liste des blocs doit etre une liste non vide.")
    if not isinstance(inodes, list) or not inodes:
        raise ValueError("La table d'inodes doit etre une liste non vide.")

    # Tous les blocs non vides doivent deja etre du Base64 et tenir dans un cadre.
    for numero in range(len(blocs)):
        bloc = blocs[numero]
        if bloc is not None:
            contenu = _decoder_bloc(bloc)
            if len(contenu) == 0 or len(contenu) > taille_bloc:
                raise ValueError("La taille d'un bloc occupe est incoherente.")

    noms = []
    numeros = []
    blocs_utilises = []
    for position_inode in range(len(inodes)):
        inode = inodes[position_inode]
        if inode is None:
            continue
        if not isinstance(inode, dict):
            raise ValueError("Un inode doit etre un dictionnaire ou None.")
        champs = ["numero", "nom", "taille", "blocs"]
        for champ in champs:
            if champ not in inode:
                raise ValueError("Il manque " + champ + " dans un inode.")

        numero_inode = inode["numero"]
        nom = inode["nom"]
        taille = inode["taille"]
        liste_blocs = inode["blocs"]
        if numero_inode != position_inode + 1:
            raise ValueError("Le numero d'inode ne correspond pas a sa case.")
        if isinstance(numero_inode, bool) or not isinstance(numero_inode, int):
            raise ValueError("Le numero d'inode doit etre un entier.")
        if numero_inode in numeros:
            raise ValueError("Deux inodes ont le meme numero.")
        numeros.append(numero_inode)
        _verifier_nom(nom)
        if nom in noms:
            raise ValueError("Deux inodes utilisent le meme nom.")
        noms.append(nom)
        if isinstance(taille, bool) or not isinstance(taille, int) or taille < 0:
            raise ValueError("La taille d'un inode est invalide.")
        if not isinstance(liste_blocs, list):
            raise ValueError("La liste de blocs d'un inode est invalide.")

        nombre_attendu = (taille + taille_bloc - 1) // taille_bloc
        if len(liste_blocs) != nombre_attendu:
            raise ValueError("Le nombre de blocs ne correspond pas a la taille du fichier.")

        contenu_fichier = b""
        for position_bloc in range(len(liste_blocs)):
            numero_bloc = liste_blocs[position_bloc]
            if isinstance(numero_bloc, bool) or not isinstance(numero_bloc, int):
                raise ValueError("Le numero de bloc doit etre un entier.")
            if numero_bloc < 0 or numero_bloc >= len(blocs):
                raise ValueError("Un inode pointe en dehors du disque.")
            if numero_bloc in blocs_utilises:
                raise ValueError("Un bloc ne peut appartenir qu'a un seul inode.")
            blocs_utilises.append(numero_bloc)

            bloc = blocs[numero_bloc]
            if bloc is None:
                raise ValueError("Un inode pointe vers un bloc libre.")
            morceau = _decoder_bloc(bloc)
            if position_bloc < len(liste_blocs) - 1 and len(morceau) != taille_bloc:
                raise ValueError("Seul le dernier bloc d'un fichier peut etre incomplet.")
            contenu_fichier += morceau

        if len(contenu_fichier) != taille:
            raise ValueError("La taille d'un fichier ne correspond pas a ses blocs.")
        try:
            contenu_fichier.decode("utf-8")
        except UnicodeDecodeError:
            raise ValueError("Le contenu d'un fichier n'est pas du texte UTF-8.")

    for numero in range(len(blocs)):
        if blocs[numero] is not None and numero not in blocs_utilises:
            raise ValueError("Un bloc occupe n'est reference par aucun inode.")


def _charger_image_canonique(image):
    """Convertit le schema publie anglais vers le dictionnaire francais interne."""
    if image.get("schema") != SCHEMA or image.get("version") != VERSION:
        raise ValueError("Cette image ESINOS n'utilise pas le schema version 1.")
    champs = ["block_size", "block_count", "max_inodes", "blocks", "inodes"]
    for champ in champs:
        if champ not in image:
            raise ValueError("Il manque " + champ + " dans l'image ESINOS.")

    taille_bloc = image["block_size"]
    nombre_blocs = image["block_count"]
    nombre_inodes = image["max_inodes"]
    blocs = image["blocks"]
    inodes_source = image["inodes"]
    _verifier_entier_positif(taille_bloc, "block_size")
    _verifier_entier_positif(nombre_blocs, "block_count")
    _verifier_entier_positif(nombre_inodes, "max_inodes")
    if not isinstance(blocs, list) or len(blocs) != nombre_blocs:
        raise ValueError("Le nombre de blocs de l'image ESINOS est incoherent.")
    if not isinstance(inodes_source, list) or len(inodes_source) > nombre_inodes:
        raise ValueError("La table d'inodes ESINOS est incoherente.")

    disque = {
        "taille_bloc": taille_bloc,
        "blocs": list(blocs),
        "inodes": [None] * nombre_inodes,
    }
    for inode_source in inodes_source:
        if not isinstance(inode_source, dict):
            raise ValueError("Un inode ESINOS doit etre un dictionnaire.")
        champs_inode = ["inode_id", "name", "size", "blocks"]
        for champ in champs_inode:
            if champ not in inode_source:
                raise ValueError("Il manque " + champ + " dans un inode ESINOS.")

        numero = inode_source["inode_id"]
        if isinstance(numero, bool) or not isinstance(numero, int):
            raise ValueError("Le numero d'inode ESINOS est invalide.")
        if numero < 1 or numero > nombre_inodes:
            raise ValueError("Le numero d'inode ESINOS est hors limites.")
        if disque["inodes"][numero - 1] is not None:
            raise ValueError("Deux inodes ESINOS utilisent le meme numero.")
        disque["inodes"][numero - 1] = {
            "numero": numero,
            "nom": inode_source["name"],
            "taille": inode_source["size"],
            "blocs": list(inode_source["blocks"]),
        }

    _verifier_image(disque)
    return disque


def _charger_image_debutant(image):
    """Relit la premiere image d'atelier, dont les blocs etaient en hexadecimal."""
    champs = ["taille_bloc", "blocs", "inodes"]
    for champ in champs:
        if champ not in image:
            raise ValueError("Il manque " + champ + " dans l'image de l'atelier.")
    taille_bloc = image["taille_bloc"]
    blocs_source = image["blocs"]
    inodes_source = image["inodes"]
    _verifier_entier_positif(taille_bloc, "La taille de bloc")
    if not isinstance(blocs_source, list) or not isinstance(inodes_source, list):
        raise ValueError("Les blocs et les inodes de l'atelier doivent etre des listes.")

    disque = {"taille_bloc": taille_bloc, "blocs": [], "inodes": []}
    for bloc_hexadecimal in blocs_source:
        if bloc_hexadecimal is None:
            disque["blocs"].append(None)
        else:
            if not isinstance(bloc_hexadecimal, str):
                raise ValueError("Un bloc hexadecimal doit etre du texte.")
            try:
                octets = bytes.fromhex(bloc_hexadecimal)
            except ValueError:
                raise ValueError("Un bloc de l'atelier n'est pas hexadecimal.")
            disque["blocs"].append(_encoder_bloc(octets))

    for inode_source in inodes_source:
        if inode_source is None:
            disque["inodes"].append(None)
        else:
            if not isinstance(inode_source, dict):
                raise ValueError("Un inode de l'atelier doit etre un dictionnaire.")
            champs_inode = ["numero", "nom", "taille", "blocs"]
            for champ in champs_inode:
                if champ not in inode_source:
                    raise ValueError("Il manque " + champ + " dans un inode de l'atelier.")
            disque["inodes"].append({
                "numero": inode_source["numero"],
                "nom": inode_source["nom"],
                "taille": inode_source["taille"],
                "blocs": list(inode_source["blocs"]),
            })

    _verifier_image(disque)
    return disque


def charger(chemin):
    """Charge une image ancienne ou canonique et retourne le disque francais."""
    try:
        with open(chemin, "r", encoding="utf-8") as fichier:
            image = json.load(fichier)
    except FileNotFoundError:
        raise FileNotFoundError("Image disque introuvable : " + str(chemin))
    except (OSError, json.JSONDecodeError) as erreur:
        raise ValueError("Impossible de lire l'image disque : " + str(erreur))

    if not isinstance(image, dict):
        raise ValueError("Cette image doit contenir un dictionnaire JSON.")
    if image.get("schema") == SCHEMA:
        return _charger_image_canonique(image)
    if "taille_bloc" in image:
        return _charger_image_debutant(image)
    raise ValueError("Image disque inconnue : schema ESINOS absent.")


def _image_canonique(disque):
    """Traduit le disque francais en schema version 1 du projet publie."""
    inodes_canonique = []
    for inode in disque["inodes"]:
        if inode is not None:
            inodes_canonique.append({
                "inode_id": inode["numero"],
                "name": inode["nom"],
                "size": inode["taille"],
                "blocks": list(inode["blocs"]),
            })
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "block_size": disque["taille_bloc"],
        "block_count": len(disque["blocs"]),
        "max_inodes": len(disque["inodes"]),
        "inodes": inodes_canonique,
        "blocks": list(disque["blocs"]),
    }


def _ecrire_temporaire(chemin, image):
    """Ecrit d'abord un JSON complet dans le repertoire de destination."""
    destination = os.path.abspath(str(chemin))
    dossier = os.path.dirname(destination)
    nom = os.path.basename(destination)
    try:
        os.makedirs(dossier, exist_ok=True)
        descripteur, temporaire = tempfile.mkstemp(
            prefix="." + nom + ".", suffix=".tmp", dir=dossier, text=True
        )
    except OSError as erreur:
        raise OSError("Impossible de preparer l'image disque : " + str(erreur))

    try:
        with os.fdopen(descripteur, "w", encoding="utf-8") as fichier:
            json.dump(image, fichier, ensure_ascii=False, indent=2, sort_keys=True)
            fichier.write("\n")
            fichier.flush()
            os.fsync(fichier.fileno())
    except OSError as erreur:
        try:
            os.unlink(temporaire)
        except OSError:
            pass
        raise OSError("Impossible d'ecrire l'image disque : " + str(erreur))
    return temporaire, destination


def _supprimer_temporaire(temporaire):
    try:
        os.unlink(temporaire)
    except FileNotFoundError:
        pass
    except OSError:
        pass


def sauvegarder(chemin, disque):
    """Valide puis remplace l'image entiere d'un seul coup."""
    _verifier_image(disque)
    image = _image_canonique(disque)
    temporaire, destination = _ecrire_temporaire(chemin, image)
    try:
        os.replace(temporaire, destination)
    except OSError as erreur:
        raise OSError("Impossible de publier l'image disque : " + str(erreur))
    finally:
        _supprimer_temporaire(temporaire)


def initialiser(chemin, nombre_blocs=64, taille_bloc=64, nombre_inodes=16):
    """Cree une image neuve sans ecraser un chemin deja occupe."""
    _verifier_entier_positif(nombre_blocs, "Le nombre de blocs")
    _verifier_entier_positif(taille_bloc, "La taille de bloc")
    _verifier_entier_positif(nombre_inodes, "Le nombre d'inodes")

    disque = {
        "taille_bloc": taille_bloc,
        "blocs": [None] * nombre_blocs,
        "inodes": [None] * nombre_inodes,
    }
    _verifier_image(disque)
    image = _image_canonique(disque)
    temporaire, destination = _ecrire_temporaire(chemin, image)
    try:
        try:
            # link est atomique : deux initialisations ne peuvent pas gagner.
            os.link(temporaire, destination)
        except FileExistsError:
            raise FileExistsError("Refus d'ecraser une image disque existante.")
        except OSError as erreur:
            if erreur.errno == errno.EEXIST:
                raise FileExistsError("Refus d'ecraser une image disque existante.")
            raise OSError("Impossible de creer l'image disque : " + str(erreur))
    finally:
        _supprimer_temporaire(temporaire)
    return disque


def chercher_inode(disque, nom):
    """Renvoie l'inode qui porte ce nom, ou None s'il n'existe pas."""
    for inode in disque["inodes"]:
        if inode is not None and inode["nom"] == nom:
            return inode
    return None


def creer_fichier(chemin, nom, texte):
    """Alloue un inode et les premiers blocs libres pour un nouveau texte."""
    _verifier_nom(nom)
    if not isinstance(texte, str):
        raise ValueError("Le contenu du fichier doit etre du texte.")
    disque = charger(chemin)
    if chercher_inode(disque, nom) is not None:
        raise ValueError("Ce nom existe deja.")

    case_inode = None
    for position in range(len(disque["inodes"])):
        if disque["inodes"][position] is None:
            case_inode = position
            break
    if case_inode is None:
        raise ValueError("La table d'inodes est pleine.")

    octets = texte.encode("utf-8")
    taille_bloc = disque["taille_bloc"]
    morceaux = []
    debut = 0
    while debut < len(octets):
        morceau = octets[debut:debut + taille_bloc]
        morceaux.append(_encoder_bloc(morceau))
        debut += taille_bloc

    libres = []
    for numero in range(len(disque["blocs"])):
        if disque["blocs"][numero] is None:
            libres.append(numero)
    if len(morceaux) > len(libres):
        raise ValueError("Le disque virtuel manque de blocs libres.")

    blocs_inode = []
    for position in range(len(morceaux)):
        numero_bloc = libres[position]
        disque["blocs"][numero_bloc] = morceaux[position]
        blocs_inode.append(numero_bloc)

    inode = {
        "numero": case_inode + 1,
        "nom": nom,
        "taille": len(octets),
        "blocs": blocs_inode,
    }
    disque["inodes"][case_inode] = inode
    sauvegarder(chemin, disque)
    return inode


def lire_fichier(chemin, nom):
    """Suit les numeros de blocs d'un inode et reconstitue le texte UTF-8."""
    disque = charger(chemin)
    inode = chercher_inode(disque, nom)
    if inode is None:
        raise ValueError("Fichier introuvable : " + str(nom))

    octets = b""
    for numero_bloc in inode["blocs"]:
        octets += _decoder_bloc(disque["blocs"][numero_bloc])
    try:
        return octets.decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError("Le fichier ne contient pas du texte UTF-8.")


def supprimer_fichier(chemin, nom):
    """Libere les blocs et la case d'inode d'un fichier."""
    disque = charger(chemin)
    inode = chercher_inode(disque, nom)
    if inode is None:
        raise ValueError("Fichier introuvable : " + str(nom))

    for numero_bloc in inode["blocs"]:
        disque["blocs"][numero_bloc] = None
    disque["inodes"][inode["numero"] - 1] = None
    sauvegarder(chemin, disque)


def lister_inodes(chemin):
    """Retourne toutes les cases de la table, y compris les cases libres."""
    disque = charger(chemin)
    return disque["inodes"]


def etat_disque(chemin):
    """Calcule des compteurs simples pour le menu interactif."""
    disque = charger(chemin)
    blocs_utilises = 0
    for bloc in disque["blocs"]:
        if bloc is not None:
            blocs_utilises += 1
    inodes_utilises = 0
    for inode in disque["inodes"]:
        if inode is not None:
            inodes_utilises += 1
    return {
        "taille_bloc": disque["taille_bloc"],
        "nombre_blocs": len(disque["blocs"]),
        "blocs_utilises": blocs_utilises,
        "blocs_libres": len(disque["blocs"]) - blocs_utilises,
        "nombre_inodes": len(disque["inodes"]),
        "inodes_utilises": inodes_utilises,
        "inodes_libres": len(disque["inodes"]) - inodes_utilises,
    }


def reformater(chemin):
    """Efface volontairement tous les fichiers mais garde la meme geometrie."""
    ancien = charger(chemin)
    disque = {
        "taille_bloc": ancien["taille_bloc"],
        "blocs": [None] * len(ancien["blocs"]),
        "inodes": [None] * len(ancien["inodes"]),
    }
    sauvegarder(chemin, disque)
    return disque
