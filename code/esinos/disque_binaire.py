"""Codec binaire pedagogique du mini-disque ESINOS.

Le dictionnaire echange avec le reste du projet garde les noms francais du
disque JSON. L'image binaire reserve, dans cet ordre, un superbloc, un bitmap,
une table d'inodes, un repertoire, puis les donnees. Chaque zone commence sur
un bloc physique : la carte peut donc montrer S, B, I, R et D sans bloc
partage. Les numeros dans les inodes restent logiques. Le bloc logique 0 est
le bloc physique ``data_start``.

Chaque inode garde un pointeur direct par bloc de donnees. C'est moins compact
qu'un vrai Unix, mais plus facile a expliquer et cela ne diminue pas la
capacite d'une image JSON existante.
"""

import base64
import binascii
import struct
import zlib


MAGIC = b"ESINOSB1"
VERSION = 1

# 64 octets : signature, version, geometrie, offsets, CRC des donnees et CRC
# du superbloc. Les zones qui suivent commencent toujours sur un bloc entier.
HEADER_FORMAT = ">8sHH" + "I" * 13
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

INODE_PREFIX_FORMAT = ">B3xI"
INODE_PREFIX_SIZE = struct.calcsize(INODE_PREFIX_FORMAT)
DIRECTORY_PREFIX_FORMAT = ">IHH"
DIRECTORY_PREFIX_SIZE = struct.calcsize(DIRECTORY_PREFIX_FORMAT)
NOM_MAX_OCTETS = 64
DIRECTORY_RECORD_SIZE = DIRECTORY_PREFIX_SIZE + NOM_MAX_OCTETS
POINTEUR_ABSENT = 0xFFFFFFFF

# Bornes avant allocation. La limite de 64 Mio concerne les donnees et l'image
# complete, car une enorme table de pointeurs serait elle aussi peu pedagogique.
MAX_TAILLE_BLOC = 65536
MAX_BLOCS_DONNEES = 65536
MAX_INODES = 4096
MAX_TAILLE_DONNEES = 64 * 1024 * 1024
MAX_TAILLE_IMAGE = 64 * 1024 * 1024


def _div_haut(nombre, diviseur):
    """Renvoie le quotient arrondi vers le haut."""
    return (nombre + diviseur - 1) // diviseur


def _verifier_entier(valeur, etiquette, minimum, maximum):
    """Controle un entier, sans accepter les booleens Python."""
    if isinstance(valeur, bool) or not isinstance(valeur, int):
        raise ValueError(etiquette + " doit etre un entier.")
    if valeur < minimum or valeur > maximum:
        raise ValueError(etiquette + " est hors limites.")


def _tous_zero(octets):
    """Retourne True seulement si tous les octets valent zero."""
    for octet in octets:
        if octet != 0:
            return False
    return True


def _decoder_base64(texte):
    """Decode un bloc JSON Base64 avec une erreur volontairement simple."""
    if not isinstance(texte, str) or texte == "":
        raise ValueError("Un bloc occupe doit etre du Base64 non vide.")
    try:
        return base64.b64decode(texte.encode("ascii"), validate=True)
    except (UnicodeEncodeError, ValueError, binascii.Error):
        raise ValueError("Un bloc occupe n'est pas du Base64 valide.")


def _nom_ascii(nom):
    """Encode un nom de repertoire dans la zone fixe de 64 octets."""
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
    """Calcule les cadres physiques sans allouer l'image."""
    _verifier_entier(taille_bloc, "La taille de bloc", 1, MAX_TAILLE_BLOC)
    _verifier_entier(
        nombre_blocs, "Le nombre de blocs de donnees", 1, MAX_BLOCS_DONNEES
    )
    _verifier_entier(nombre_inodes, "Le nombre d'inodes", 1, MAX_INODES)
    if taille_bloc * nombre_blocs > MAX_TAILLE_DONNEES:
        raise ValueError("Les donnees du disque depassent 64 Mio.")

    taille_bitmap = _div_haut(nombre_blocs, 8)
    taille_inode = INODE_PREFIX_SIZE + 4 * nombre_blocs
    taille_table_inodes = taille_inode * nombre_inodes
    taille_table_repertoire = DIRECTORY_RECORD_SIZE * nombre_inodes

    blocs_superbloc = _div_haut(HEADER_SIZE, taille_bloc)
    bloc_bitmap = blocs_superbloc
    blocs_bitmap = _div_haut(taille_bitmap, taille_bloc)
    bloc_inodes = bloc_bitmap + blocs_bitmap
    blocs_inodes = _div_haut(taille_table_inodes, taille_bloc)
    bloc_repertoire = bloc_inodes + blocs_inodes
    blocs_repertoire = _div_haut(taille_table_repertoire, taille_bloc)
    data_start = bloc_repertoire + blocs_repertoire
    blocs_metadonnees = data_start
    nombre_blocs_physiques = data_start + nombre_blocs
    taille_image = nombre_blocs_physiques * taille_bloc

    if taille_image > MAX_TAILLE_IMAGE:
        raise ValueError("La geometrie binaire demanderait une image trop grande.")

    return {
        "taille_bloc": taille_bloc,
        "nombre_blocs_donnees": nombre_blocs,
        "nombre_inodes": nombre_inodes,
        "taille_superbloc": HEADER_SIZE,
        "taille_bitmap": taille_bitmap,
        "taille_inode": taille_inode,
        "taille_repertoire": DIRECTORY_RECORD_SIZE,
        "taille_table_inodes": taille_table_inodes,
        "taille_table_repertoire": taille_table_repertoire,
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
        "blocs_metadonnees": blocs_metadonnees,
        "data_start": data_start,
        "bloc_donnees_0_physique": data_start,
        "nombre_blocs_physiques": nombre_blocs_physiques,
        "taille_image": taille_image,
    }


def _preparer_disque(disque):
    """Verifie le dictionnaire francais et prepare ses octets Base64."""
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

    geometrie = _calculer_geometrie(taille_bloc, len(blocs), len(inodes))
    nombre_blocs = geometrie["nombre_blocs_donnees"]
    nombre_inodes = geometrie["nombre_inodes"]

    octets_blocs = [None] * nombre_blocs
    for numero_bloc in range(nombre_blocs):
        bloc = blocs[numero_bloc]
        if bloc is not None:
            contenu = _decoder_base64(bloc)
            if len(contenu) > taille_bloc:
                raise ValueError("Un bloc occupe depasse la taille de bloc.")
            octets_blocs[numero_bloc] = contenu

    proprietaire = [-1] * nombre_blocs
    noms = []
    inodes_prepares = [None] * nombre_inodes
    for position_inode in range(nombre_inodes):
        inode = inodes[position_inode]
        if inode is None:
            continue
        if not isinstance(inode, dict):
            raise ValueError("Un inode doit etre un dictionnaire ou None.")
        for cle in ["numero", "nom", "taille", "blocs"]:
            if cle not in inode:
                raise ValueError("Il manque " + cle + " dans un inode.")

        numero = inode["numero"]
        taille = inode["taille"]
        liste_blocs = inode["blocs"]
        _verifier_entier(numero, "Le numero d'inode", 1, nombre_inodes)
        if numero != position_inode + 1:
            raise ValueError("Le numero d'inode ne correspond pas a sa case.")
        nom_octets = _nom_ascii(inode["nom"])
        if inode["nom"] in noms:
            raise ValueError("Deux inodes utilisent le meme nom.")
        noms.append(inode["nom"])
        _verifier_entier(taille, "La taille d'un fichier", 0,
                         taille_bloc * nombre_blocs)
        if not isinstance(liste_blocs, list):
            raise ValueError("La liste de blocs d'un inode est invalide.")

        nombre_attendu = _div_haut(taille, taille_bloc)
        if len(liste_blocs) != nombre_attendu:
            raise ValueError("Le nombre de blocs ne correspond pas a la taille.")

        contenu_fichier = b""
        pointeurs = []
        for position_bloc in range(len(liste_blocs)):
            numero_bloc = liste_blocs[position_bloc]
            _verifier_entier(numero_bloc, "Le numero de bloc", 0,
                             nombre_blocs - 1)
            if proprietaire[numero_bloc] != -1:
                raise ValueError("Un bloc ne peut appartenir qu'a un seul inode.")
            if octets_blocs[numero_bloc] is None:
                raise ValueError("Un inode pointe vers un bloc libre.")
            morceau = octets_blocs[numero_bloc]
            if position_bloc < len(liste_blocs) - 1:
                if len(morceau) != taille_bloc:
                    raise ValueError("Seul le dernier bloc peut etre incomplet.")
            proprietaire[numero_bloc] = position_inode
            pointeurs.append(numero_bloc)
            contenu_fichier += morceau

        if len(contenu_fichier) != taille:
            raise ValueError("La taille du fichier ne correspond pas a ses blocs.")
        try:
            contenu_fichier.decode("utf-8")
        except UnicodeDecodeError:
            raise ValueError("Le contenu d'un fichier doit etre du texte UTF-8.")
        inodes_prepares[position_inode] = {
            "numero": numero,
            "nom": inode["nom"],
            "nom_octets": nom_octets,
            "taille": taille,
            "blocs": pointeurs,
        }

    for numero_bloc in range(nombre_blocs):
        if octets_blocs[numero_bloc] is not None:
            if proprietaire[numero_bloc] == -1:
                raise ValueError("Un bloc occupe n'est reference par aucun inode.")

    return {
        "geometrie": geometrie,
        "octets_blocs": octets_blocs,
        "proprietaire": proprietaire,
        "inodes": inodes_prepares,
    }


def geometrie(disque):
    """Retourne la geometrie physique d'un disque francais valide.

    Tous les debuts de zone sont alignes : S, B, I, R puis donnees. Le nombre
    de blocs de donnees reste la capacite logique demandee dans le JSON.
    """
    preparation = _preparer_disque(disque)
    return dict(preparation["geometrie"])


def _ecrire_pointeurs_absents(image, geometrie_image):
    """Initialise tous les pointeurs directs avec la sentinelle 0xFFFFFFFF."""
    nombre_blocs = geometrie_image["nombre_blocs_donnees"]
    nombre_inodes = geometrie_image["nombre_inodes"]
    taille_inode = geometrie_image["taille_inode"]
    offset_inodes = geometrie_image["offset_inodes"]
    for position_inode in range(nombre_inodes):
        depart = offset_inodes + position_inode * taille_inode
        for position_pointeur in range(nombre_blocs):
            offset = depart + INODE_PREFIX_SIZE + 4 * position_pointeur
            struct.pack_into(">I", image, offset, POINTEUR_ABSENT)


def _ecrire_entete(image, geometrie_image):
    """Pose les deux CRC une fois tout le reste de l'image ecrit."""
    crc_donnees = zlib.crc32(bytes(image[HEADER_SIZE:])) & 0xFFFFFFFF
    champs = (
        MAGIC,
        VERSION,
        HEADER_SIZE,
        geometrie_image["taille_bloc"],
        geometrie_image["nombre_blocs_donnees"],
        geometrie_image["nombre_inodes"],
        geometrie_image["blocs_metadonnees"],
        geometrie_image["offset_bitmap"],
        geometrie_image["taille_bitmap"],
        geometrie_image["offset_inodes"],
        geometrie_image["taille_table_inodes"],
        geometrie_image["offset_repertoire"],
        geometrie_image["taille_table_repertoire"],
        geometrie_image["data_start"],
        crc_donnees,
        0,
    )
    entete_sans_crc = struct.pack(HEADER_FORMAT, *champs)
    crc_entete = zlib.crc32(entete_sans_crc[:-4]) & 0xFFFFFFFF
    champs = champs[:-1] + (crc_entete,)
    image[:HEADER_SIZE] = struct.pack(HEADER_FORMAT, *champs)


def encoder(disque):
    """Encode le dictionnaire francais dans une image binaire complete."""
    preparation = _preparer_disque(disque)
    geometrie_image = preparation["geometrie"]
    nombre_blocs = geometrie_image["nombre_blocs_donnees"]
    nombre_inodes = geometrie_image["nombre_inodes"]
    taille_bloc = geometrie_image["taille_bloc"]
    image = bytearray(geometrie_image["taille_image"])

    _ecrire_pointeurs_absents(image, geometrie_image)
    for numero_bloc in range(nombre_blocs):
        if preparation["proprietaire"][numero_bloc] != -1:
            position_octet = geometrie_image["offset_bitmap"] + numero_bloc // 8
            bit = 7 - numero_bloc % 8
            image[position_octet] |= 1 << bit

    for position_inode in range(nombre_inodes):
        inode = preparation["inodes"][position_inode]
        if inode is None:
            continue
        position_inode_octet = (
            geometrie_image["offset_inodes"]
            + position_inode * geometrie_image["taille_inode"]
        )
        struct.pack_into(
            INODE_PREFIX_FORMAT,
            image,
            position_inode_octet,
            1,
            inode["taille"],
        )
        for position_pointeur in range(len(inode["blocs"])):
            struct.pack_into(
                ">I",
                image,
                position_inode_octet + INODE_PREFIX_SIZE + 4 * position_pointeur,
                inode["blocs"][position_pointeur],
            )

        position_repertoire = (
            geometrie_image["offset_repertoire"]
            + position_inode * DIRECTORY_RECORD_SIZE
        )
        struct.pack_into(
            DIRECTORY_PREFIX_FORMAT,
            image,
            position_repertoire,
            inode["numero"],
            len(inode["nom_octets"]),
            0,
        )
        debut_nom = position_repertoire + DIRECTORY_PREFIX_SIZE
        fin_nom = debut_nom + len(inode["nom_octets"])
        image[debut_nom:fin_nom] = inode["nom_octets"]

    for numero_bloc in range(nombre_blocs):
        contenu = preparation["octets_blocs"][numero_bloc]
        if contenu is None:
            continue
        position = (geometrie_image["data_start"] + numero_bloc) * taille_bloc
        image[position:position + len(contenu)] = contenu

    _ecrire_entete(image, geometrie_image)
    return bytes(image)


def _lire_entete(image):
    """Lit et valide le superbloc avant toute allocation dependant de lui."""
    if len(image) < HEADER_SIZE:
        raise ValueError("Image binaire trop courte pour contenir un superbloc.")
    champs = struct.unpack(HEADER_FORMAT, image[:HEADER_SIZE])
    if champs[0] != MAGIC:
        raise ValueError("La signature de l'image binaire est inconnue.")
    if champs[1] != VERSION:
        raise ValueError("La version de l'image binaire est inconnue.")
    if champs[2] != HEADER_SIZE:
        raise ValueError("La taille du superbloc est invalide.")
    crc_entete = zlib.crc32(image[:HEADER_SIZE - 4]) & 0xFFFFFFFF
    if champs[15] != crc_entete:
        raise ValueError("Le CRC du superbloc est invalide.")
    return champs


def _verifier_geometrie_entete(champs, taille_image):
    """Compare les offsets annonces a la geometrie recalculee."""
    geometrie_image = _calculer_geometrie(champs[3], champs[4], champs[5])
    valeurs = [
        (champs[6], geometrie_image["blocs_metadonnees"]),
        (champs[7], geometrie_image["offset_bitmap"]),
        (champs[8], geometrie_image["taille_bitmap"]),
        (champs[9], geometrie_image["offset_inodes"]),
        (champs[10], geometrie_image["taille_table_inodes"]),
        (champs[11], geometrie_image["offset_repertoire"]),
        (champs[12], geometrie_image["taille_table_repertoire"]),
        (champs[13], geometrie_image["data_start"]),
    ]
    for annoncee, calculee in valeurs:
        if annoncee != calculee:
            raise ValueError("Les offsets de l'image binaire sont incoherents.")
    if taille_image != geometrie_image["taille_image"]:
        raise ValueError("La taille de l'image binaire est incoherente.")
    return geometrie_image


def _verifier_padding_metadonnees(image, geometrie_image):
    """Refuse toute donnee cachee dans le remplissage des zones S, B, I ou R."""
    zones = [
        (HEADER_SIZE, geometrie_image["offset_bitmap"]),
        (
            geometrie_image["offset_bitmap"] + geometrie_image["taille_bitmap"],
            geometrie_image["offset_inodes"],
        ),
        (
            geometrie_image["offset_inodes"]
            + geometrie_image["taille_table_inodes"],
            geometrie_image["offset_repertoire"],
        ),
        (
            geometrie_image["offset_repertoire"]
            + geometrie_image["taille_table_repertoire"],
            geometrie_image["data_start"] * geometrie_image["taille_bloc"],
        ),
    ]
    for debut, fin in zones:
        if not _tous_zero(image[debut:fin]):
            raise ValueError("Le remplissage des metadonnees est invalide.")


def _verifier_bitmap(bitmap, nombre_blocs, utilises):
    """Compare chaque bit du bitmap aux pointeurs effectivement rencontres."""
    for numero_bloc in range(nombre_blocs):
        bit = 7 - numero_bloc % 8
        occupe = (bitmap[numero_bloc // 8] & (1 << bit)) != 0
        if occupe != utilises[numero_bloc]:
            raise ValueError("Le bitmap ne correspond pas aux pointeurs d'inodes.")
    reste = nombre_blocs % 8
    if reste != 0:
        masque_bits_inutiles = (1 << (8 - reste)) - 1
        if bitmap[-1] & masque_bits_inutiles:
            raise ValueError("Le bitmap reserve des blocs inexistants.")


def _lire_inodes_et_repertoire(image, geometrie_image):
    """Reconstruit les inodes et controle leurs pointeurs et leurs noms."""
    nombre_blocs = geometrie_image["nombre_blocs_donnees"]
    nombre_inodes = geometrie_image["nombre_inodes"]
    taille_bloc = geometrie_image["taille_bloc"]
    taille_inode = geometrie_image["taille_inode"]
    inodes = [None] * nombre_inodes
    longueurs_blocs = [0] * nombre_blocs
    utilises = [False] * nombre_blocs
    noms = []

    for position_inode in range(nombre_inodes):
        position_inode_octet = (
            geometrie_image["offset_inodes"] + position_inode * taille_inode
        )
        actif, taille = struct.unpack_from(
            INODE_PREFIX_FORMAT, image, position_inode_octet
        )
        if not _tous_zero(
            image[position_inode_octet + 1:position_inode_octet + 4]
        ):
            raise ValueError("Les octets reserves d'un inode doivent etre nuls.")
        position_repertoire = (
            geometrie_image["offset_repertoire"]
            + position_inode * DIRECTORY_RECORD_SIZE
        )
        numero_repertoire, longueur_nom, reserve = struct.unpack_from(
            DIRECTORY_PREFIX_FORMAT, image, position_repertoire
        )

        pointeurs = []
        for position_pointeur in range(nombre_blocs):
            pointeur = struct.unpack_from(
                ">I",
                image,
                position_inode_octet + INODE_PREFIX_SIZE + 4 * position_pointeur,
            )[0]
            pointeurs.append(pointeur)

        if actif == 0:
            if taille != 0:
                raise ValueError("Un inode libre annonce une taille non nulle.")
            for pointeur in pointeurs:
                if pointeur != POINTEUR_ABSENT:
                    raise ValueError("Un inode libre contient un pointeur.")
            if not _tous_zero(
                image[position_repertoire:position_repertoire + DIRECTORY_RECORD_SIZE]
            ):
                raise ValueError("Un inode libre possede une entree de repertoire.")
            continue
        if actif != 1:
            raise ValueError("L'etat d'un inode est invalide.")
        if taille > taille_bloc * nombre_blocs:
            raise ValueError("La taille d'un inode est hors limites.")
        if reserve != 0 or longueur_nom == 0 or longueur_nom > NOM_MAX_OCTETS:
            raise ValueError("L'entree de repertoire est invalide.")
        if numero_repertoire != position_inode + 1:
            raise ValueError("Le repertoire ne correspond pas a la table d'inodes.")
        debut_nom = position_repertoire + DIRECTORY_PREFIX_SIZE
        nom_octets = image[debut_nom:debut_nom + longueur_nom]
        zone_nom = image[debut_nom:debut_nom + NOM_MAX_OCTETS]
        if not _tous_zero(zone_nom[longueur_nom:]) or b"\x00" in nom_octets:
            raise ValueError("Le remplissage du nom de fichier est invalide.")
        try:
            nom = nom_octets.decode("ascii")
        except UnicodeDecodeError:
            raise ValueError("Un nom de fichier n'est pas ASCII.")
        if nom in noms:
            raise ValueError("Deux entrees de repertoire ont le meme nom.")
        noms.append(nom)

        nombre_pointeurs = _div_haut(taille, taille_bloc)
        liste_blocs = []
        for position_pointeur in range(nombre_blocs):
            pointeur = pointeurs[position_pointeur]
            if position_pointeur >= nombre_pointeurs:
                if pointeur != POINTEUR_ABSENT:
                    raise ValueError("Un pointeur direct inutile n'est pas vide.")
                continue
            if pointeur >= nombre_blocs:
                raise ValueError("Un inode pointe en dehors des donnees.")
            if utilises[pointeur]:
                raise ValueError("Un bloc de donnees est partage par deux inodes.")
            utilises[pointeur] = True
            liste_blocs.append(pointeur)
            longueur = taille_bloc
            if position_pointeur == nombre_pointeurs - 1:
                longueur = taille - taille_bloc * (nombre_pointeurs - 1)
            longueurs_blocs[pointeur] = longueur

        inodes[position_inode] = {
            "numero": position_inode + 1,
            "nom": nom,
            "taille": taille,
            "blocs": liste_blocs,
        }
    return inodes, utilises, longueurs_blocs


def _lire_blocs(image, geometrie_image, utilises, longueurs_blocs):
    """Controle le padding physique et reconstitue les textes Base64 logiques."""
    taille_bloc = geometrie_image["taille_bloc"]
    nombre_blocs = geometrie_image["nombre_blocs_donnees"]
    morceaux = [None] * nombre_blocs
    blocs = [None] * nombre_blocs
    for numero_bloc in range(nombre_blocs):
        debut = (geometrie_image["data_start"] + numero_bloc) * taille_bloc
        brut = image[debut:debut + taille_bloc]
        if not utilises[numero_bloc]:
            if not _tous_zero(brut):
                raise ValueError("Un bloc libre contient des donnees.")
            continue
        longueur = longueurs_blocs[numero_bloc]
        if longueur <= 0 or longueur > taille_bloc:
            raise ValueError("La longueur logique d'un bloc est invalide.")
        if not _tous_zero(brut[longueur:]):
            raise ValueError("Le remplissage d'un bloc de donnees est invalide.")
        morceau = brut[:longueur]
        morceaux[numero_bloc] = morceau
        blocs[numero_bloc] = base64.b64encode(morceau).decode("ascii")
    return blocs, morceaux


def _verifier_textes(inodes, morceaux):
    """Verifie que chaque fichier reconstruit est une chaine UTF-8 complete."""
    for inode in inodes:
        if inode is None:
            continue
        contenu = b""
        for numero_bloc in inode["blocs"]:
            contenu += morceaux[numero_bloc]
        if len(contenu) != inode["taille"]:
            raise ValueError("La taille du fichier binaire est incoherente.")
        try:
            contenu.decode("utf-8")
        except UnicodeDecodeError:
            raise ValueError("Le contenu d'un fichier n'est pas du texte UTF-8.")


def decoder(data):
    """Decode et valide entierement une image binaire ESINOS."""
    if not isinstance(data, (bytes, bytearray)):
        raise ValueError("Une image binaire doit etre une suite d'octets.")
    image = bytes(data)
    champs = _lire_entete(image)
    geometrie_image = _verifier_geometrie_entete(champs, len(image))
    crc_donnees = zlib.crc32(image[HEADER_SIZE:]) & 0xFFFFFFFF
    if champs[14] != crc_donnees:
        raise ValueError("Le CRC des donnees de l'image est invalide.")

    _verifier_padding_metadonnees(image, geometrie_image)
    debut_bitmap = geometrie_image["offset_bitmap"]
    fin_bitmap = debut_bitmap + geometrie_image["taille_bitmap"]
    bitmap = image[debut_bitmap:fin_bitmap]
    inodes, utilises, longueurs_blocs = _lire_inodes_et_repertoire(
        image, geometrie_image
    )
    _verifier_bitmap(bitmap, geometrie_image["nombre_blocs_donnees"], utilises)
    blocs, morceaux = _lire_blocs(
        image, geometrie_image, utilises, longueurs_blocs
    )
    _verifier_textes(inodes, morceaux)
    return {
        "taille_bloc": geometrie_image["taille_bloc"],
        "blocs": blocs,
        "inodes": inodes,
    }
