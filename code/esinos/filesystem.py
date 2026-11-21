"""Mini système de fichiers persistant : blocs, inodes et un fichier JSON."""

import json
import os
import tempfile


MAX_BLOCS = 65536
MAX_INODES = 4096
MAX_TAILLE_BLOC = 65536
MAX_DONNEES = 64 * 1024 * 1024


def _entier(valeur, nom, minimum, maximum):
    if isinstance(valeur, bool) or not isinstance(valeur, int):
        raise ValueError(nom + " doit être un entier.")
    if valeur < minimum or valeur > maximum:
        raise ValueError(nom + " est hors limites.")


def _verifier_nom(nom):
    if not isinstance(nom, str) or nom == "" or "\x00" in nom:
        raise ValueError("Nom de fichier invalide.")
    if len(nom.encode("utf-8")) > 64:
        raise ValueError("Le nom de fichier dépasse 64 octets UTF-8.")


def _valider(disque):
    """Vérifie les liens inode -> blocs puis renvoie une copie simple."""
    if not isinstance(disque, dict):
        raise ValueError("Le disque doit être un dictionnaire.")
    for cle in ("taille_bloc", "blocs", "inodes"):
        if cle not in disque:
            raise ValueError("Il manque " + cle + " dans le disque.")
    taille_bloc = disque["taille_bloc"]
    blocs = disque["blocs"]
    inodes = disque["inodes"]
    _entier(taille_bloc, "La taille de bloc", 1, MAX_TAILLE_BLOC)
    if not isinstance(blocs, list) or not isinstance(inodes, list):
        raise ValueError("Les blocs et les inodes doivent être des listes.")
    _entier(len(blocs), "Le nombre de blocs", 1, MAX_BLOCS)
    _entier(len(inodes), "Le nombre d'inodes", 1, MAX_INODES)
    if taille_bloc * len(blocs) > MAX_DONNEES:
        raise ValueError("La capacité du disque dépasse 64 Mio.")

    blocs_valides = [None] * len(blocs)
    for numero in range(len(blocs)):
        bloc = blocs[numero]
        if bloc is None:
            continue
        if not isinstance(bloc, list) or not bloc or len(bloc) > taille_bloc:
            raise ValueError("Un bloc occupé est invalide.")
        copie = []
        for octet in bloc:
            _entier(octet, "Un octet", 0, 255)
            copie.append(octet)
        blocs_valides[numero] = copie

    proprietaires = [-1] * len(blocs)
    noms = []
    inodes_valides = [None] * len(inodes)
    for position in range(len(inodes)):
        inode = inodes[position]
        if inode is None:
            continue
        if not isinstance(inode, dict):
            raise ValueError("Un inode doit être un dictionnaire ou None.")
        for cle in ("numero", "nom", "taille", "blocs"):
            if cle not in inode:
                raise ValueError("Il manque " + cle + " dans un inode.")
        _entier(inode["numero"], "Le numéro d'inode", 1, len(inodes))
        if inode["numero"] != position + 1:
            raise ValueError("Le numéro d'inode ne correspond pas à sa case.")
        _verifier_nom(inode["nom"])
        if inode["nom"] in noms:
            raise ValueError("Deux inodes utilisent le même nom.")
        noms.append(inode["nom"])
        _entier(inode["taille"], "La taille d'un fichier", 0,
                taille_bloc * len(blocs))
        references = inode["blocs"]
        if not isinstance(references, list):
            raise ValueError("La liste de blocs d'un inode est invalide.")
        attendu = (inode["taille"] + taille_bloc - 1) // taille_bloc
        if len(references) != attendu:
            raise ValueError("Le nombre de blocs ne correspond pas à la taille.")

        morceaux = []
        pointeurs = []
        for ordre in range(len(references)):
            numero = references[ordre]
            _entier(numero, "Le numéro de bloc", 0, len(blocs) - 1)
            if proprietaires[numero] != -1:
                raise ValueError("Un bloc appartient à plusieurs inodes.")
            bloc = blocs_valides[numero]
            if bloc is None:
                raise ValueError("Un inode pointe vers un bloc libre.")
            if ordre + 1 < len(references) and len(bloc) != taille_bloc:
                raise ValueError("Seul le dernier bloc peut être incomplet.")
            proprietaires[numero] = position
            pointeurs.append(numero)
            morceaux.extend(bloc)
        if len(morceaux) != inode["taille"]:
            raise ValueError("La taille du fichier ne correspond pas à ses blocs.")
        try:
            bytes(morceaux).decode("utf-8")
        except UnicodeDecodeError:
            raise ValueError("Le contenu d'un fichier n'est pas du texte UTF-8.")
        inodes_valides[position] = {
            "numero": position + 1,
            "nom": inode["nom"],
            "taille": inode["taille"],
            "blocs": pointeurs,
        }

    for numero in range(len(blocs)):
        if blocs_valides[numero] is not None and proprietaires[numero] == -1:
            raise ValueError("Un bloc occupé n'est référencé par aucun inode.")
    return {
        "taille_bloc": taille_bloc,
        "blocs": blocs_valides,
        "inodes": inodes_valides,
    }


def _ecrire(chemin, contenu, nouveau=False):
    """Publie un JSON complet, sans remplacer une image neuve existante."""
    destination = os.path.abspath(os.fspath(chemin))
    dossier = os.path.dirname(destination)
    os.makedirs(dossier, exist_ok=True)
    descripteur, temporaire = tempfile.mkstemp(
        prefix=".esinos.", suffix=".tmp", dir=dossier
    )
    try:
        with os.fdopen(descripteur, "wb") as fichier:
            fichier.write(contenu)
            fichier.flush()
            os.fsync(fichier.fileno())
        if nouveau:
            os.link(temporaire, destination)
        else:
            os.replace(temporaire, destination)
    finally:
        try:
            os.unlink(temporaire)
        except FileNotFoundError:
            pass


def sauvegarder(chemin, disque):
    """Valide le modèle avant de remplacer atomiquement son fichier JSON."""
    disque = _valider(disque)
    texte = json.dumps(disque, ensure_ascii=False, indent=2) + "\n"
    _ecrire(chemin, texte.encode("utf-8"))


def initialiser(chemin, nombre_blocs=64, taille_bloc=64, nombre_inodes=16):
    """Crée une image vide exclusivement, pour ne jamais l'écraser par erreur."""
    _entier(nombre_blocs, "Le nombre de blocs", 1, MAX_BLOCS)
    _entier(taille_bloc, "La taille de bloc", 1, MAX_TAILLE_BLOC)
    _entier(nombre_inodes, "Le nombre d'inodes", 1, MAX_INODES)
    if taille_bloc * nombre_blocs > MAX_DONNEES:
        raise ValueError("La capacité du disque dépasse 64 Mio.")
    disque = {
        "taille_bloc": taille_bloc,
        "blocs": [None] * nombre_blocs,
        "inodes": [None] * nombre_inodes,
    }
    disque = _valider(disque)
    texte = json.dumps(disque, ensure_ascii=False, indent=2) + "\n"
    _ecrire(chemin, texte.encode("utf-8"), nouveau=True)
    return disque


def charger(chemin):
    """Lit une image JSON française sans la modifier."""
    try:
        with open(chemin, "r", encoding="utf-8") as fichier:
            disque = json.load(fichier)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as erreur:
        raise ValueError("Image disque illisible : " + str(erreur))
    return _valider(disque)


def chercher_inode(disque, nom):
    for inode in disque["inodes"]:
        if inode is not None and inode["nom"] == nom:
            return inode
    return None


def creer_fichier(chemin, nom, texte):
    """Encode le texte UTF-8, prend les premiers blocs libres et crée un inode."""
    _verifier_nom(nom)
    if not isinstance(texte, str):
        raise ValueError("Le contenu doit être du texte.")
    disque = charger(chemin)
    if chercher_inode(disque, nom) is not None:
        raise ValueError("Ce nom existe déjà.")
    if None not in disque["inodes"]:
        raise ValueError("La table d'inodes est pleine.")
    contenu = list(texte.encode("utf-8"))
    taille_bloc = disque["taille_bloc"]
    besoin = (len(contenu) + taille_bloc - 1) // taille_bloc
    libres = []
    for numero in range(len(disque["blocs"])):
        if disque["blocs"][numero] is None:
            libres.append(numero)
    if besoin > len(libres):
        raise ValueError("Le disque manque de blocs libres.")

    pointeurs = libres[:besoin]
    for ordre in range(len(pointeurs)):
        debut = ordre * taille_bloc
        disque["blocs"][pointeurs[ordre]] = contenu[debut:debut + taille_bloc]
    position = disque["inodes"].index(None)
    inode = {
        "numero": position + 1,
        "nom": nom,
        "taille": len(contenu),
        "blocs": pointeurs,
    }
    disque["inodes"][position] = inode
    sauvegarder(chemin, disque)
    return inode


def lire_fichier(chemin, nom):
    """Assemble les octets de tous les blocs avant le décodage UTF-8."""
    disque = charger(chemin)
    inode = chercher_inode(disque, nom)
    if inode is None:
        raise ValueError("Fichier introuvable : " + str(nom))
    contenu = []
    for numero in inode["blocs"]:
        contenu.extend(disque["blocs"][numero])
    return bytes(contenu).decode("utf-8")


def supprimer_fichier(chemin, nom):
    disque = charger(chemin)
    inode = chercher_inode(disque, nom)
    if inode is None:
        raise ValueError("Fichier introuvable : " + str(nom))
    for numero in inode["blocs"]:
        disque["blocs"][numero] = None
    disque["inodes"][inode["numero"] - 1] = None
    sauvegarder(chemin, disque)


def lister_inodes(chemin):
    return charger(chemin)["inodes"]
