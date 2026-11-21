"""Tests du codec binaire pedagogique, sans ecriture de fichier disque."""

import base64
import struct
import sys
import unittest
import zlib
from pathlib import Path


CODE = Path(__file__).resolve().parents[1]
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

import esinos.disque_binaire as binaire


def bloc(octets):
    """Fabrique une valeur Base64 du modele JSON francais."""
    return base64.b64encode(octets).decode("ascii")


def recalculer_crc(image):
    """Conserve des CRC valides pour tester les controles semantiques."""
    champs = list(
        struct.unpack(
            binaire.HEADER_FORMAT, bytes(image[:binaire.HEADER_SIZE])
        )
    )
    champs[14] = zlib.crc32(bytes(image[binaire.HEADER_SIZE:])) & 0xFFFFFFFF
    champs[15] = 0
    entete = struct.pack(binaire.HEADER_FORMAT, *champs)
    champs[15] = zlib.crc32(entete[:-4]) & 0xFFFFFFFF
    image[:binaire.HEADER_SIZE] = struct.pack(binaire.HEADER_FORMAT, *champs)


def modifier_champ_entete(image, position, valeur):
    """Change un champ du superbloc puis le rend coherent au niveau CRC."""
    champs = list(
        struct.unpack(
            binaire.HEADER_FORMAT, bytes(image[:binaire.HEADER_SIZE])
        )
    )
    champs[position] = valeur
    image[:binaire.HEADER_SIZE] = struct.pack(binaire.HEADER_FORMAT, *champs)
    recalculer_crc(image)


class DisqueBinaireTests(unittest.TestCase):
    def test_roundtrip_utf8_et_fichier_vide(self):
        disque = {
            "taille_bloc": 3,
            "blocs": [
                bloc(b"\xc3\xa9A"), bloc(b"bc"), bloc(b"\x00"), None,
            ],
            "inodes": [
                {"numero": 1, "nom": "accent.txt", "taille": 5,
                 "blocs": [0, 1]},
                {"numero": 2, "nom": "vide.txt", "taille": 0,
                 "blocs": []},
                {"numero": 3, "nom": "nul.txt", "taille": 1,
                 "blocs": [2]},
            ],
        }
        image = binaire.encoder(disque)
        self.assertTrue(image.startswith(binaire.MAGIC))
        self.assertEqual(binaire.verifier(disque), disque)
        self.assertEqual(binaire.decoder(image), disque)

    def test_tres_petits_blocs_et_geometrie_physique(self):
        disque = {
            "taille_bloc": 2,
            "blocs": [bloc(b"a\xc3"), bloc(b"\xa9"), None],
            "inodes": [
                {"numero": 1, "nom": "utf8.txt", "taille": 3,
                 "blocs": [0, 1]},
                None,
            ],
        }
        geometrie = binaire.geometrie(disque)
        image = binaire.encoder(disque)
        self.assertGreater(geometrie["data_start"], 0)
        self.assertEqual(
            geometrie["bloc_donnees_0_physique"], geometrie["data_start"]
        )
        self.assertEqual(len(image), geometrie["taille_image"])
        self.assertEqual(geometrie["nombre_blocs_donnees"], 3)
        for cle in ["offset_bitmap", "offset_inodes", "offset_repertoire"]:
            self.assertEqual(geometrie[cle] % disque["taille_bloc"], 0)
        self.assertEqual(binaire.decoder(image), disque)

    def test_inode_garde_un_pointeur_direct_par_bloc_de_donnees(self):
        disque = {
            "taille_bloc": 2,
            "blocs": [bloc(b"ab"), bloc(b"cd"), bloc(b"ef"), bloc(b"gh")],
            "inodes": [
                {"numero": 1, "nom": "plein.txt", "taille": 8,
                 "blocs": [0, 1, 2, 3]},
            ],
        }
        geometrie = binaire.geometrie(disque)
        self.assertEqual(geometrie["taille_inode"], 8 + 4 * 4)
        self.assertEqual(binaire.decoder(binaire.encoder(disque)), disque)

    def test_crc_detecte_une_alteration_accidentelle(self):
        disque = {
            "taille_bloc": 4,
            "blocs": [bloc(b"test"), None],
            "inodes": [
                {"numero": 1, "nom": "a.txt", "taille": 4, "blocs": [0]},
            ],
        }
        image = bytearray(binaire.encoder(disque))
        image[-1] ^= 1
        with self.assertRaises(ValueError):
            binaire.decoder(image)

    def test_bitmap_incoherent_est_refuse_meme_avec_crc_recalcules(self):
        disque = {
            "taille_bloc": 4,
            "blocs": [bloc(b"test"), None, None],
            "inodes": [
                {"numero": 1, "nom": "a.txt", "taille": 4, "blocs": [0]},
            ],
        }
        geometrie = binaire.geometrie(disque)
        image = bytearray(binaire.encoder(disque))
        image[geometrie["offset_bitmap"]] ^= 0x80
        recalculer_crc(image)
        with self.assertRaises(ValueError):
            binaire.decoder(image)

        bits_inutiles = bytearray(binaire.encoder(disque))
        bits_inutiles[geometrie["offset_bitmap"]] |= 0x01
        recalculer_crc(bits_inutiles)
        with self.assertRaises(ValueError):
            binaire.decoder(bits_inutiles)

    def test_repertoire_et_inode_incoherents_sont_refuses(self):
        disque = {
            "taille_bloc": 4,
            "blocs": [bloc(b"test"), None],
            "inodes": [
                {"numero": 1, "nom": "a.txt", "taille": 4, "blocs": [0]},
                None,
            ],
        }
        geometrie = binaire.geometrie(disque)
        repertoire = bytearray(binaire.encoder(disque))
        struct.pack_into(">I", repertoire, geometrie["offset_repertoire"], 0)
        recalculer_crc(repertoire)
        with self.assertRaises(ValueError):
            binaire.decoder(repertoire)

        inode = bytearray(binaire.encoder(disque))
        struct.pack_into(">I", inode, geometrie["offset_inodes"] + 8, 1)
        recalculer_crc(inode)
        with self.assertRaises(ValueError):
            binaire.decoder(inode)

        for position_reservee in [
            geometrie["offset_inodes"] + 1,
            geometrie["offset_inodes"] + geometrie["taille_inode"] + 1,
        ]:
            reserve = bytearray(binaire.encoder(disque))
            reserve[position_reservee] = 1
            recalculer_crc(reserve)
            with self.assertRaises(ValueError):
                binaire.decoder(reserve)

        nom_nul = bytearray(binaire.encoder(disque))
        debut_nom = geometrie["offset_repertoire"] + 8
        nom_nul[debut_nom + 1] = 0
        recalculer_crc(nom_nul)
        with self.assertRaises(ValueError):
            binaire.decoder(nom_nul)

    def test_bloc_libre_et_padding_sont_controles(self):
        disque = {
            "taille_bloc": 4,
            "blocs": [bloc(b"ok"), None],
            "inodes": [
                {"numero": 1, "nom": "a.txt", "taille": 2, "blocs": [0]},
            ],
        }
        geometrie = binaire.geometrie(disque)
        image = bytearray(binaire.encoder(disque))
        position_libre = (geometrie["data_start"] + 1) * 4
        image[position_libre] = ord("X")
        recalculer_crc(image)
        with self.assertRaises(ValueError):
            binaire.decoder(image)

        padding = bytearray(binaire.encoder(disque))
        position_occupe = geometrie["data_start"] * 4
        padding[position_occupe + 2] = ord("X")
        recalculer_crc(padding)
        with self.assertRaises(ValueError):
            binaire.decoder(padding)

    def test_entete_taille_et_offsets_restent_stricts(self):
        disque = {
            "taille_bloc": 4,
            "blocs": [bloc(b"test"), None],
            "inodes": [
                {"numero": 1, "nom": "a.txt", "taille": 4, "blocs": [0]},
            ],
        }
        image = binaire.encoder(disque)
        with self.assertRaises(ValueError):
            binaire.decoder(b"x" * 63)

        tronquee = bytearray(image)
        tronquee.pop()
        recalculer_crc(tronquee)
        with self.assertRaises(ValueError):
            binaire.decoder(tronquee)

        suffixe = bytearray(image)
        suffixe.append(0)
        recalculer_crc(suffixe)
        with self.assertRaises(ValueError):
            binaire.decoder(suffixe)

        version = bytearray(image)
        modifier_champ_entete(version, 1, binaire.VERSION + 1)
        with self.assertRaises(ValueError):
            binaire.decoder(version)

        offset = bytearray(image)
        modifier_champ_entete(offset, 7, 0)
        with self.assertRaises(ValueError):
            binaire.decoder(offset)

    def test_pointeurs_et_validations_d_entree_sont_stricts(self):
        disque = {
            "taille_bloc": 2,
            "blocs": [bloc(b"ab"), bloc(b"cd")],
            "inodes": [
                {"numero": 1, "nom": "double.txt", "taille": 4,
                 "blocs": [0, 1]},
            ],
        }
        geometrie = binaire.geometrie(disque)
        doublon = bytearray(binaire.encoder(disque))
        struct.pack_into(">I", doublon, geometrie["offset_inodes"] + 12, 0)
        recalculer_crc(doublon)
        with self.assertRaises(ValueError):
            binaire.decoder(doublon)

        hors_limite = bytearray(binaire.encoder(disque))
        struct.pack_into(">I", hors_limite, geometrie["offset_inodes"] + 12, 2)
        recalculer_crc(hors_limite)
        with self.assertRaises(ValueError):
            binaire.decoder(hors_limite)

        bool_taille = {"taille_bloc": True, "blocs": [None],
                       "inodes": [None]}
        with self.assertRaises(ValueError):
            binaire.encoder(bool_taille)
        with self.assertRaises(ValueError):
            binaire.decoder(True)
        with self.assertRaises(ValueError):
            binaire._calculer_geometrie(65536, 65536, 1)
        with self.assertRaises(ValueError):
            binaire._calculer_geometrie(1, 65536, 4096)

    def test_noms_ascii_limites_et_utf8_fractionne(self):
        disque = {
            "taille_bloc": 1,
            "blocs": [None],
            "inodes": [
                {"numero": 1, "nom": "a" * 64, "taille": 0,
                 "blocs": []},
            ],
        }
        self.assertEqual(binaire.decoder(binaire.encoder(disque)), disque)

        trop_long = {
            "taille_bloc": 1,
            "blocs": [None],
            "inodes": [
                {"numero": 1, "nom": "a" * 65, "taille": 0,
                 "blocs": []},
            ],
        }
        nom_nul = {
            "taille_bloc": 1,
            "blocs": [None],
            "inodes": [
                {"numero": 1, "nom": "a\x00b", "taille": 0,
                 "blocs": []},
            ],
        }
        nom_non_ascii = {
            "taille_bloc": 1,
            "blocs": [None],
            "inodes": [
                {"numero": 1, "nom": "é.txt", "taille": 0,
                 "blocs": []},
            ],
        }
        for invalide in [trop_long, nom_nul, nom_non_ascii]:
            with self.assertRaises(ValueError):
                binaire.encoder(invalide)


if __name__ == "__main__":
    unittest.main()
