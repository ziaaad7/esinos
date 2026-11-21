"""Fichiers à inodes, lecture des images et publication atomique."""
import base64
import json
import os
import re
import tempfile
from .disque_binaire import MAGIC, encoder, decoder, geometrie, verifier

SCHEMA = "esinos-mini-filesystem"
NOM_SIMPLE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
TAILLE_MAX_IMAGE = 64 * 1024 * 1024


def _verifier_nom(nom):
    if not isinstance(nom, str) or NOM_SIMPLE.fullmatch(nom) is None:
        raise ValueError("Nom invalide : 1 à 64 lettres, chiffres, points, _ ou -.")


def _valider(disque):
    disque = verifier(disque)
    for inode in disque["inodes"]:
        if inode is not None:
            _verifier_nom(inode["nom"])
    return disque


def _depuis_json(image):
    """Les deux anciens JSON sont convertis vers le même modèle en mémoire."""
    try:
        if image.get("schema") == SCHEMA and image.get("version") == 1:
            blocs = image["blocks"]
            nombre = image["max_inodes"]
            if type(nombre) is not int or not 1 <= nombre <= 4096:
                raise ValueError("Nombre d'inodes invalide.")
            if type(image["block_count"]) is not int:
                raise ValueError("Le nombre de blocs doit être entier.")
            if not isinstance(blocs, list) or len(blocs) != image["block_count"]:
                raise ValueError("Nombre de blocs incohérent.")
            disque = {"taille_bloc": image["block_size"],
                      "blocs": blocs, "inodes": [None] * nombre}
            for inode in image["inodes"]:
                numero = inode["inode_id"]
                if type(numero) is not int or not 1 <= numero <= nombre:
                    raise ValueError("Numéro d'inode invalide.")
                if disque["inodes"][numero - 1] is not None:
                    raise ValueError("Numéro d'inode déjà utilisé.")
                disque["inodes"][numero - 1] = {
                    "numero": numero, "nom": inode["name"],
                    "taille": inode["size"], "blocs": inode["blocks"],
                }
        elif "taille_bloc" in image:
            blocs = []
            for morceau in image["blocs"]:
                if morceau is not None:
                    morceau = base64.b64encode(bytes.fromhex(morceau)).decode("ascii")
                blocs.append(morceau)
            disque = {"taille_bloc": image["taille_bloc"],
                      "blocs": blocs, "inodes": image["inodes"]}
        else:
            raise ValueError("Format JSON ESINOS inconnu.")
        return _valider(disque)
    except (KeyError, TypeError, AttributeError) as erreur:
        raise ValueError("Image JSON invalide : " + str(erreur))


def format_disque(chemin):
    with open(chemin, "rb") as fichier:
        return "binaire" if fichier.read(len(MAGIC)) == MAGIC else "json"


def charger(chemin):
    """Charge le binaire actuel ou un ancien JSON, sans modifier le fichier."""
    with open(chemin, "rb") as fichier:
        contenu = fichier.read(TAILLE_MAX_IMAGE + 1)
    if len(contenu) > TAILLE_MAX_IMAGE:
        raise ValueError("L'image dépasse 64 Mio.")
    if contenu.startswith(MAGIC):
        return _valider(decoder(contenu))
    try:
        image = json.loads(contenu.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        raise ValueError("Image disque illisible.")
    if not isinstance(image, dict):
        raise ValueError("L'image JSON doit être un dictionnaire.")
    return _depuis_json(image)


def _ecrire(chemin, contenu, nouveau=False):
    """Écrit une image complète puis la publie, avec création exclusive si demandée."""
    destination = os.path.abspath(str(chemin))
    dossier = os.path.dirname(destination)
    os.makedirs(dossier, exist_ok=True)
    fd, temporaire = tempfile.mkstemp(prefix=".esinos.", suffix=".tmp", dir=dossier)
    try:
        with os.fdopen(fd, "wb") as fichier:
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
    disque = _valider(disque)
    if format_disque(chemin) == "binaire":
        contenu = encoder(disque)
    else:
        inodes = []
        for inode in disque["inodes"]:
            if inode is not None:
                inodes.append({"inode_id": inode["numero"], "name": inode["nom"],
                               "size": inode["taille"], "blocks": inode["blocs"]})
        image = {"schema": SCHEMA, "version": 1,
                 "block_size": disque["taille_bloc"], "block_count": len(disque["blocs"]),
                 "max_inodes": len(disque["inodes"]), "blocks": disque["blocs"],
                 "inodes": inodes}
        contenu = (json.dumps(image, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    _ecrire(chemin, contenu)


def initialiser(chemin, nombre_blocs=64, taille_bloc=64, nombre_inodes=16):
    for valeur, limite in ((nombre_blocs, 65536), (taille_bloc, 65536),
                           (nombre_inodes, 4096)):
        if type(valeur) is not int or not 1 <= valeur <= limite:
            raise ValueError("Géométrie du disque invalide.")
    disque = {"taille_bloc": taille_bloc, "blocs": [None] * nombre_blocs,
              "inodes": [None] * nombre_inodes}
    _ecrire(chemin, encoder(disque), nouveau=True)
    return disque


def migrer_json(source, destination):
    if format_disque(source) != "json":
        raise ValueError("La source doit être une image JSON.")
    disque = charger(source)
    _ecrire(destination, encoder(disque), nouveau=True)
    return disque


def chercher_inode(disque, nom):
    for inode in disque["inodes"]:
        if inode is not None and inode["nom"] == nom:
            return inode
    return None


def creer_fichier(chemin, nom, texte):
    _verifier_nom(nom)
    if not isinstance(texte, str):
        raise ValueError("Le contenu doit être du texte.")
    disque = charger(chemin)
    if chercher_inode(disque, nom) is not None:
        raise ValueError("Ce nom existe déjà.")
    if None not in disque["inodes"]:
        raise ValueError("La table d'inodes est pleine.")
    contenu = texte.encode("utf-8")
    taille_bloc = disque["taille_bloc"]
    nombre = (len(contenu) + taille_bloc - 1) // taille_bloc
    libres = []
    for numero, bloc in enumerate(disque["blocs"]):
        if bloc is None:
            libres.append(numero)
    if nombre > len(libres):
        raise ValueError("Le disque manque de blocs libres.")
    numeros = libres[:nombre]
    for position, numero in enumerate(numeros):
        morceau = contenu[position * taille_bloc:(position + 1) * taille_bloc]
        disque["blocs"][numero] = base64.b64encode(morceau).decode("ascii")
    place = disque["inodes"].index(None)
    inode = {"numero": place + 1, "nom": nom, "taille": len(contenu), "blocs": numeros}
    disque["inodes"][place] = inode
    sauvegarder(chemin, disque)
    return inode


def lire_fichier(chemin, nom):
    disque = charger(chemin)
    inode = chercher_inode(disque, nom)
    if inode is None:
        raise ValueError("Fichier introuvable : " + str(nom))
    contenu = b""
    for numero in inode["blocs"]:
        contenu += base64.b64decode(disque["blocs"][numero])
    return contenu.decode("utf-8")


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


def etat_disque(chemin):
    disque = charger(chemin)
    blocs = disque["blocs"]
    inodes = disque["inodes"]
    format_image = format_disque(chemin)
    return {"format": format_image,
            "geometrie": geometrie(disque) if format_image == "binaire" else None,
            "taille_bloc": disque["taille_bloc"], "nombre_blocs": len(blocs),
            "blocs_utilises": len(blocs) - blocs.count(None),
            "blocs_libres": blocs.count(None), "nombre_inodes": len(inodes),
            "inodes_utilises": len(inodes) - inodes.count(None),
            "inodes_libres": inodes.count(None)}


def reformater(chemin):
    disque = charger(chemin)
    disque["blocs"] = [None] * len(disque["blocs"])
    disque["inodes"] = [None] * len(disque["inodes"])
    sauvegarder(chemin, disque)
    return disque
