"""Format binaire canonique du mini-disque ESINOS.

Les blocs vus par les inodes restent logiques. Dans l'image, les zones S, B,
I, R et D occupent chacune des blocs physiques distincts et alignes.
"""

import base64
import binascii
import struct
import zlib


MAGIC = b"ESINOSB1"
VERSION = 1
HEADER_FORMAT = ">8sHH" + "I" * 13
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
INODE_PREFIX_FORMAT = ">B3xI"
INODE_PREFIX_SIZE = struct.calcsize(INODE_PREFIX_FORMAT)
DIRECTORY_PREFIX_FORMAT = ">IHH"
DIRECTORY_PREFIX_SIZE = struct.calcsize(DIRECTORY_PREFIX_FORMAT)
NOM_MAX_OCTETS = 64
DIRECTORY_RECORD_SIZE = DIRECTORY_PREFIX_SIZE + NOM_MAX_OCTETS
POINTEUR_ABSENT = 0xFFFFFFFF
MAX_TAILLE_BLOC = 65536
MAX_BLOCS_DONNEES = 65536
MAX_INODES = 4096
MAX_TAILLE_DONNEES = 64 * 1024 * 1024
MAX_TAILLE_IMAGE = 64 * 1024 * 1024


def _haut(nombre, diviseur):
    return (nombre + diviseur - 1) // diviseur


def _entier(valeur, nom, minimum, maximum):
    if isinstance(valeur, bool) or not isinstance(valeur, int):
        raise ValueError(nom + " doit etre un entier.")
    if valeur < minimum or valeur > maximum:
        raise ValueError(nom + " est hors limites.")


def _base64(texte):
    if not isinstance(texte, str) or texte == "":
        raise ValueError("Un bloc occupe doit etre du Base64 non vide.")
    try:
        return base64.b64decode(texte.encode("ascii"), validate=True)
    except (UnicodeEncodeError, ValueError, binascii.Error):
        raise ValueError("Un bloc occupe n'est pas du Base64 valide.")


def _nom(nom):
    if not isinstance(nom, str) or nom == "":
        raise ValueError("Le nom d'un fichier est invalide.")
    try:
        octets = nom.encode("ascii")
    except UnicodeEncodeError:
        raise ValueError("Le nom d'un fichier doit etre ASCII.")
    if len(octets) > NOM_MAX_OCTETS or b"\x00" in octets:
        raise ValueError("Le nom d'un fichier est trop long ou contient NUL.")
    return octets


def _calculer_geometrie(taille_bloc, nombre_blocs, nombre_inodes):
    """Calcule tous les cadres sans allouer l'image."""
    _entier(taille_bloc, "La taille de bloc", 1, MAX_TAILLE_BLOC)
    _entier(nombre_blocs, "Le nombre de blocs de donnees", 1,
            MAX_BLOCS_DONNEES)
    _entier(nombre_inodes, "Le nombre d'inodes", 1, MAX_INODES)
    if taille_bloc * nombre_blocs > MAX_TAILLE_DONNEES:
        raise ValueError("Les donnees du disque depassent 64 Mio.")

    bitmap = _haut(nombre_blocs, 8)
    taille_inode = INODE_PREFIX_SIZE + 4 * nombre_blocs
    table_inodes = taille_inode * nombre_inodes
    table_repertoire = DIRECTORY_RECORD_SIZE * nombre_inodes
    blocs_superbloc = _haut(HEADER_SIZE, taille_bloc)
    bloc_bitmap = blocs_superbloc
    blocs_bitmap = _haut(bitmap, taille_bloc)
    bloc_inodes = bloc_bitmap + blocs_bitmap
    blocs_inodes = _haut(table_inodes, taille_bloc)
    bloc_repertoire = bloc_inodes + blocs_inodes
    blocs_repertoire = _haut(table_repertoire, taille_bloc)
    data_start = bloc_repertoire + blocs_repertoire
    physiques = data_start + nombre_blocs
    taille_image = physiques * taille_bloc
    if taille_image > MAX_TAILLE_IMAGE:
        raise ValueError("La geometrie binaire demanderait une image trop grande.")

    return {
        "taille_bloc": taille_bloc,
        "nombre_blocs_donnees": nombre_blocs,
        "nombre_inodes": nombre_inodes,
        "taille_superbloc": HEADER_SIZE,
        "taille_bitmap": bitmap,
        "taille_inode": taille_inode,
        "taille_repertoire": DIRECTORY_RECORD_SIZE,
        "taille_table_inodes": table_inodes,
        "taille_table_repertoire": table_repertoire,
        "bloc_superbloc": 0,
        "blocs_superbloc": blocs_superbloc,
        "bloc_bitmap": bloc_bitmap,
        "blocs_bitmap": blocs_bitmap,
        "bloc_inodes": bloc_inodes,
        "blocs_inodes": blocs_inodes,
        "bloc_repertoire": bloc_repertoire,
        "blocs_repertoire": blocs_repertoire,
        "offset_bitmap": bloc_bitmap * taille_bloc,
        "offset_inodes": bloc_inodes * taille_bloc,
        "offset_repertoire": bloc_repertoire * taille_bloc,
        "blocs_metadonnees": data_start,
        "data_start": data_start,
        "bloc_donnees_0_physique": data_start,
        "nombre_blocs_physiques": physiques,
        "taille_image": taille_image,
    }


def _preparer(disque):
    """Valide le modele et retourne sa forme Base64 canonique et ses octets."""
    if not isinstance(disque, dict):
        raise ValueError("Le disque doit etre un dictionnaire.")
    for cle in ["taille_bloc", "blocs", "inodes"]:
        if cle not in disque:
            raise ValueError("Il manque " + cle + " dans le disque.")
    taille_bloc = disque["taille_bloc"]
    blocs = disque["blocs"]
    inodes = disque["inodes"]
    if not isinstance(blocs, list) or not isinstance(inodes, list):
        raise ValueError("Les blocs et les inodes doivent etre des listes.")
    geo = _calculer_geometrie(taille_bloc, len(blocs), len(inodes))
    nombre_blocs = geo["nombre_blocs_donnees"]
    donnees = [None] * nombre_blocs
    for numero in range(nombre_blocs):
        if blocs[numero] is not None:
            morceau = _base64(blocs[numero])
            if len(morceau) > taille_bloc:
                raise ValueError("Un bloc occupe depasse la taille de bloc.")
            donnees[numero] = morceau

    proprietaires = [-1] * nombre_blocs
    noms = []
    inodes_canoniques = [None] * geo["nombre_inodes"]
    for position in range(geo["nombre_inodes"]):
        inode = inodes[position]
        if inode is None:
            continue
        if not isinstance(inode, dict):
            raise ValueError("Un inode doit etre un dictionnaire ou None.")
        for cle in ["numero", "nom", "taille", "blocs"]:
            if cle not in inode:
                raise ValueError("Il manque " + cle + " dans un inode.")
        _entier(inode["numero"], "Le numero d'inode", 1,
                geo["nombre_inodes"])
        if inode["numero"] != position + 1:
            raise ValueError("Le numero d'inode ne correspond pas a sa case.")
        nom = inode["nom"]
        _nom(nom)
        if nom in noms:
            raise ValueError("Deux inodes utilisent le meme nom.")
        noms.append(nom)
        _entier(inode["taille"], "La taille d'un fichier", 0,
                taille_bloc * nombre_blocs)
        references = inode["blocs"]
        if not isinstance(references, list):
            raise ValueError("La liste de blocs d'un inode est invalide.")
        attendu = _haut(inode["taille"], taille_bloc)
        if len(references) != attendu:
            raise ValueError("Le nombre de blocs ne correspond pas a la taille.")

        morceaux = []
        pointeurs = []
        for ordre in range(attendu):
            numero = references[ordre]
            _entier(numero, "Le numero de bloc", 0, nombre_blocs - 1)
            if proprietaires[numero] != -1:
                raise ValueError("Un bloc ne peut appartenir qu'a un seul inode.")
            morceau = donnees[numero]
            if morceau is None:
                raise ValueError("Un inode pointe vers un bloc libre.")
            if ordre + 1 < attendu and len(morceau) != taille_bloc:
                raise ValueError("Seul le dernier bloc peut etre incomplet.")
            proprietaires[numero] = position
            pointeurs.append(numero)
            morceaux.append(morceau)
        contenu = b"".join(morceaux)
        if len(contenu) != inode["taille"]:
            raise ValueError("La taille du fichier ne correspond pas a ses blocs.")
        try:
            contenu.decode("utf-8")
        except UnicodeDecodeError:
            raise ValueError("Le contenu d'un fichier doit etre du texte UTF-8.")
        inodes_canoniques[position] = {
            "numero": position + 1,
            "nom": nom,
            "taille": inode["taille"],
            "blocs": pointeurs,
        }

    blocs_canoniques = [None] * nombre_blocs
    for numero in range(nombre_blocs):
        if donnees[numero] is not None:
            if proprietaires[numero] == -1:
                raise ValueError("Un bloc occupe n'est reference par aucun inode.")
            blocs_canoniques[numero] = base64.b64encode(
                donnees[numero]
            ).decode("ascii")
    return {
        "taille_bloc": taille_bloc,
        "blocs": blocs_canoniques,
        "inodes": inodes_canoniques,
    }, geo, donnees, proprietaires


def verifier(disque):
    """Valide un modele et retourne une copie francais/Base64 canonique."""
    canonique, _, _, _ = _preparer(disque)
    return canonique


def geometrie(disque):
    """Retourne la geometrie S/B/I/R/D d'un modele valide."""
    _, geo, _, _ = _preparer(disque)
    return dict(geo)


def _image(canonique, geo, donnees, proprietaires):
    """Construit l'unique image binaire canonique du modele deja valide."""
    nombre_blocs = geo["nombre_blocs_donnees"]
    taille_bloc = geo["taille_bloc"]
    image = bytearray(geo["taille_image"])
    absents = struct.pack(">I", POINTEUR_ABSENT) * nombre_blocs
    for position in range(geo["nombre_inodes"]):
        debut = geo["offset_inodes"] + position * geo["taille_inode"]
        image[debut + INODE_PREFIX_SIZE:debut + geo["taille_inode"]] = absents

    for numero in range(nombre_blocs):
        if proprietaires[numero] != -1:
            octet = geo["offset_bitmap"] + numero // 8
            image[octet] |= 1 << (7 - numero % 8)
    for position in range(geo["nombre_inodes"]):
        inode = canonique["inodes"][position]
        if inode is None:
            continue
        debut = geo["offset_inodes"] + position * geo["taille_inode"]
        struct.pack_into(INODE_PREFIX_FORMAT, image, debut, 1, inode["taille"])
        for ordre in range(len(inode["blocs"])):
            struct.pack_into(
                ">I", image, debut + INODE_PREFIX_SIZE + 4 * ordre,
                inode["blocs"][ordre]
            )
        nom = inode["nom"].encode("ascii")
        repertoire = geo["offset_repertoire"] + position * DIRECTORY_RECORD_SIZE
        struct.pack_into(DIRECTORY_PREFIX_FORMAT, image, repertoire,
                         inode["numero"], len(nom), 0)
        image[repertoire + DIRECTORY_PREFIX_SIZE:
              repertoire + DIRECTORY_PREFIX_SIZE + len(nom)] = nom
    for numero in range(nombre_blocs):
        if donnees[numero] is not None:
            debut = (geo["data_start"] + numero) * taille_bloc
            image[debut:debut + len(donnees[numero])] = donnees[numero]

    champs = (
        MAGIC, VERSION, HEADER_SIZE, taille_bloc, nombre_blocs,
        geo["nombre_inodes"], geo["blocs_metadonnees"],
        geo["offset_bitmap"], geo["taille_bitmap"], geo["offset_inodes"],
        geo["taille_table_inodes"], geo["offset_repertoire"],
        geo["taille_table_repertoire"], geo["data_start"],
        zlib.crc32(image[HEADER_SIZE:]) & 0xFFFFFFFF, 0,
    )
    provisoire = struct.pack(HEADER_FORMAT, *champs)
    champs = champs[:-1] + (zlib.crc32(provisoire[:-4]) & 0xFFFFFFFF,)
    image[:HEADER_SIZE] = struct.pack(HEADER_FORMAT, *champs)
    return bytes(image)


def encoder(disque):
    """Encode un modele valide en image binaire canonique."""
    canonique, geo, donnees, proprietaires = _preparer(disque)
    return _image(canonique, geo, donnees, proprietaires)


def _entete(image):
    """Verifie l'en-tete, la geometrie et les CRC avant toute reconstruction."""
    if len(image) < HEADER_SIZE:
        raise ValueError("Image binaire trop courte pour contenir un superbloc.")
    champs = struct.unpack(HEADER_FORMAT, image[:HEADER_SIZE])
    if champs[0] != MAGIC:
        raise ValueError("La signature de l'image binaire est inconnue.")
    if champs[1] != VERSION or champs[2] != HEADER_SIZE:
        raise ValueError("La version ou la taille du superbloc est invalide.")
    if champs[15] != zlib.crc32(image[:HEADER_SIZE - 4]) & 0xFFFFFFFF:
        raise ValueError("Le CRC du superbloc est invalide.")
    geo = _calculer_geometrie(champs[3], champs[4], champs[5])
    attendus = [
        (6, "blocs_metadonnees"), (7, "offset_bitmap"),
        (8, "taille_bitmap"), (9, "offset_inodes"),
        (10, "taille_table_inodes"), (11, "offset_repertoire"),
        (12, "taille_table_repertoire"), (13, "data_start"),
    ]
    for position, cle in attendus:
        if champs[position] != geo[cle]:
            raise ValueError("Les offsets de l'image binaire sont incoherents.")
    if len(image) != geo["taille_image"]:
        raise ValueError("La taille de l'image binaire est incoherente.")
    if champs[14] != zlib.crc32(image[HEADER_SIZE:]) & 0xFFFFFFFF:
        raise ValueError("Le CRC des donnees de l'image est invalide.")
    return geo


def _modele(image, geo):
    """Lit seulement les champs necessaires avant de les revalider globalement."""
    nombre_blocs = geo["nombre_blocs_donnees"]
    taille_bloc = geo["taille_bloc"]
    inodes = [None] * geo["nombre_inodes"]
    utilises = [False] * nombre_blocs
    longueurs = [0] * nombre_blocs
    for position in range(geo["nombre_inodes"]):
        debut = geo["offset_inodes"] + position * geo["taille_inode"]
        actif, taille = struct.unpack_from(INODE_PREFIX_FORMAT, image, debut)
        if actif not in [0, 1]:
            raise ValueError("L'etat d'un inode est invalide.")
        if actif == 0:
            continue
        if taille > taille_bloc * nombre_blocs:
            raise ValueError("La taille d'un inode est hors limites.")
        repertoire = geo["offset_repertoire"] + position * DIRECTORY_RECORD_SIZE
        _, longueur_nom, _ = struct.unpack_from(
            DIRECTORY_PREFIX_FORMAT, image, repertoire
        )
        if longueur_nom == 0 or longueur_nom > NOM_MAX_OCTETS:
            raise ValueError("La longueur d'un nom de fichier est invalide.")
        try:
            nom = image[repertoire + DIRECTORY_PREFIX_SIZE:
                        repertoire + DIRECTORY_PREFIX_SIZE + longueur_nom]
            nom = nom.decode("ascii")
        except UnicodeDecodeError:
            raise ValueError("Un nom de fichier n'est pas ASCII.")
        compte = _haut(taille, taille_bloc)
        pointeurs = []
        for ordre in range(compte):
            pointeur = struct.unpack_from(
                ">I", image, debut + INODE_PREFIX_SIZE + 4 * ordre
            )[0]
            if pointeur >= nombre_blocs:
                raise ValueError("Un inode pointe en dehors des donnees.")
            if utilises[pointeur]:
                raise ValueError("Un bloc de donnees est partage par deux inodes.")
            utilises[pointeur] = True
            longueurs[pointeur] = taille_bloc
            if ordre + 1 == compte:
                longueurs[pointeur] = taille - taille_bloc * (compte - 1)
            pointeurs.append(pointeur)
        inodes[position] = {
            "numero": position + 1,
            "nom": nom,
            "taille": taille,
            "blocs": pointeurs,
        }

    blocs = [None] * nombre_blocs
    for numero in range(nombre_blocs):
        if utilises[numero]:
            debut = (geo["data_start"] + numero) * taille_bloc
            blocs[numero] = base64.b64encode(
                image[debut:debut + longueurs[numero]]
            ).decode("ascii")
    return {"taille_bloc": taille_bloc, "blocs": blocs, "inodes": inodes}


def decoder(data):
    """Decode une image et refuse toute variante non canonique du format."""
    if not isinstance(data, (bytes, bytearray)):
        raise ValueError("Une image binaire doit etre une suite d'octets.")
    image = bytes(data)
    geo = _entete(image)
    modele = _modele(image, geo)
    canonique, geo, donnees, proprietaires = _preparer(modele)
    if _image(canonique, geo, donnees, proprietaires) != image:
        raise ValueError("L'image binaire n'est pas canonique.")
    return canonique
