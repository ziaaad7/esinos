"""Tests du bonus minimal : fichier JSON, blocs et inodes."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


CODE = Path(__file__).resolve().parents[1]
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from esinos.filesystem import charger, chercher_inode, creer_fichier
from esinos.filesystem import initialiser, lire_fichier, lister_inodes
from esinos.filesystem import sauvegarder, supprimer_fichier


class SystemeFichiersTests(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.TemporaryDirectory()
        self.image = Path(self.dossier.name) / "disque.img"

    def tearDown(self):
        self.dossier.cleanup()

    def test_initialisation_exclusive_et_json_francais(self):
        disque = initialiser(self.image, nombre_blocs=4, taille_bloc=3,
                             nombre_inodes=2)
        attendu = {
            "taille_bloc": 3,
            "blocs": [None, None, None, None],
            "inodes": [None, None],
        }
        self.assertEqual(disque, attendu)
        self.assertEqual(json.loads(self.image.read_text(encoding="utf-8")), attendu)
        avant = self.image.read_bytes()
        with self.assertRaises(FileExistsError):
            initialiser(self.image, 1, 1, 1)
        self.assertEqual(self.image.read_bytes(), avant)

    def test_utf8_est_assemble_avant_decodage_et_persiste(self):
        initialiser(self.image, nombre_blocs=3, taille_bloc=2,
                     nombre_inodes=3)
        inode = creer_fichier(self.image, "accent.txt", "aé")
        self.assertEqual(inode["blocs"], [0, 1])
        self.assertEqual(lire_fichier(self.image, "accent.txt"), "aé")
        brut = json.loads(self.image.read_text(encoding="utf-8"))
        self.assertEqual(brut["blocs"], [[97, 195], [169], None])
        disque = charger(self.image)
        self.assertEqual(chercher_inode(disque, "accent.txt"), inode)
        self.assertEqual(lister_inodes(self.image)[0]["nom"], "accent.txt")

    def test_suppression_libere_blocs_et_inode_reutilisable(self):
        initialiser(self.image, nombre_blocs=3, taille_bloc=2,
                     nombre_inodes=2)
        creer_fichier(self.image, "ancien.txt", "abcd")
        supprimer_fichier(self.image, "ancien.txt")
        inode = creer_fichier(self.image, "nouveau.txt", "xy")
        self.assertEqual(inode["numero"], 1)
        self.assertEqual(inode["blocs"], [0])
        self.assertEqual(lire_fichier(self.image, "nouveau.txt"), "xy")
        self.assertEqual(charger(self.image)["blocs"], [[120, 121], None, None])

    def test_capacite_et_echec_ne_modifient_pas_l_image(self):
        initialiser(self.image, nombre_blocs=2, taille_bloc=2,
                     nombre_inodes=1)
        creer_fichier(self.image, "plein.txt", "abcd")
        avant = self.image.read_bytes()
        with self.assertRaises(ValueError):
            creer_fichier(self.image, "autre.txt", "z")
        self.assertEqual(self.image.read_bytes(), avant)

        supprimer_fichier(self.image, "plein.txt")
        creer_fichier(self.image, "un.txt", "a")
        avant = self.image.read_bytes()
        with self.assertRaises(ValueError):
            creer_fichier(self.image, "deux.txt", "b")
        self.assertEqual(self.image.read_bytes(), avant)

    def test_disque_plein_est_independant_des_inodes_libres(self):
        initialiser(self.image, nombre_blocs=1, taille_bloc=1,
                     nombre_inodes=2)
        creer_fichier(self.image, "un.txt", "a")
        avant = self.image.read_bytes()
        with self.assertRaises(ValueError):
            creer_fichier(self.image, "deux.txt", "b")
        self.assertEqual(self.image.read_bytes(), avant)

    def test_fichier_vide_et_noms_uniques(self):
        initialiser(self.image, nombre_blocs=2, taille_bloc=2,
                     nombre_inodes=2)
        inode = creer_fichier(self.image, "vide.txt", "")
        self.assertEqual(inode["blocs"], [])
        self.assertEqual(lire_fichier(self.image, "vide.txt"), "")
        with self.assertRaises(ValueError):
            creer_fichier(self.image, "vide.txt", "autre")

    def test_validation_refuse_un_modele_incoherent_sans_ecrasement(self):
        initialiser(self.image, nombre_blocs=2, taille_bloc=2,
                     nombre_inodes=2)
        avant = self.image.read_bytes()
        incoherent = {
            "taille_bloc": 2,
            "blocs": [[65], None],
            "inodes": [
                {"numero": 1, "nom": "a.txt", "taille": 1, "blocs": [0]},
                {"numero": 2, "nom": "b.txt", "taille": 1, "blocs": [0]},
            ],
        }
        with self.assertRaises(ValueError):
            sauvegarder(self.image, incoherent)
        self.assertEqual(self.image.read_bytes(), avant)

    def test_json_malforme_et_geometrie_geante_sont_refuses(self):
        self.image.write_text(
            '{"taille_bloc": 2, "blocs": [[300], null], "inodes": [null]}',
            encoding="utf-8",
        )
        with self.assertRaises(ValueError):
            charger(self.image)

        self.image.write_text(
            json.dumps({
                "taille_bloc": 2,
                "blocs": [[65], None],
                "inodes": [{
                    "numero": 1, "nom": "a.txt", "taille": 1,
                    "blocs": [1],
                }],
            }),
            encoding="utf-8",
        )
        with self.assertRaises(ValueError):
            charger(self.image)

        autre = Path(self.dossier.name) / "trop-grand.json"
        with self.assertRaises(ValueError):
            initialiser(autre, 65536, 65536, 1)
        self.assertFalse(autre.exists())

    def test_echec_de_publication_garde_l_image_et_nettoie_temporaire(self):
        initialiser(self.image, nombre_blocs=2, taille_bloc=2,
                     nombre_inodes=2)
        avant = self.image.read_bytes()
        with patch("esinos.filesystem.os.replace", side_effect=OSError("stop")):
            with self.assertRaises(OSError):
                creer_fichier(self.image, "a.txt", "ok")
        self.assertEqual(self.image.read_bytes(), avant)
        self.assertEqual(list(self.image.parent.glob(".esinos.*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
