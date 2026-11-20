"""Tests des explications pedagogiques de la carte disque ESINOS."""

import json
import sys
import tempfile
import unittest
from pathlib import Path


CODE = Path(__file__).resolve().parents[1]
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from esinos.carte_disque import carte_blocs, explication_fichier
from esinos.filesystem import creer_fichier, initialiser, supprimer_fichier


class CarteDisqueTests(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.TemporaryDirectory()
        self.image = Path(self.dossier.name) / "disque.json"

    def tearDown(self):
        self.dossier.cleanup()

    def test_image_version_1_et_utf8_deux_octets(self):
        image = {
            "schema": "esinos-mini-filesystem",
            "version": 1,
            "block_size": 2,
            "block_count": 3,
            "max_inodes": 2,
            "inodes": [
                {"inode_id": 1, "name": "accent.txt", "size": 2,
                 "blocks": [0]},
            ],
            "blocks": ["w6k=", None, None],
        }
        self.image.write_text(json.dumps(image), encoding="utf-8")

        carte = carte_blocs(self.image)
        explication = explication_fichier(self.image, "accent.txt")

        self.assertIn("0-2 : #..", carte)
        self.assertIn("inode 1 (accent.txt) -> blocs 0", carte)
        self.assertIn("Taille : 2 octets", explication)
        self.assertIn("Contenu UTF-8 assemble : é", explication)
        self.assertIn("Bloc 0 : 2/2 octets occupes", explication)
        self.assertIn("Capacite inutilisee du dernier bloc : 0 octets.", explication)

    def test_utf8_reconstitue_apres_decoupage_au_milieu_d_un_caractere(self):
        initialiser(self.image, nombre_blocs=4, taille_bloc=3, nombre_inodes=2)
        inode = creer_fichier(self.image, "deux.txt", "éé")

        explication = explication_fichier(self.image, "deux.txt")

        self.assertEqual(inode["blocs"], [0, 1])
        self.assertIn("Contenu UTF-8 assemble : éé", explication)
        self.assertIn("Bloc 0 : 3/3 octets occupes", explication)
        self.assertIn("Bloc 1 : 1/3 octets occupes", explication)
        self.assertIn("Capacite inutilisee du dernier bloc : 2 octets.", explication)

    def test_suppression_reutilisation_et_lignes_de_seize_blocs(self):
        initialiser(self.image, nombre_blocs=18, taille_bloc=2, nombre_inodes=3)
        creer_fichier(self.image, "ancien.txt", "ABCD")
        supprimer_fichier(self.image, "ancien.txt")
        inode = creer_fichier(self.image, "nouveau.txt", "XY")

        carte = carte_blocs(self.image)

        self.assertEqual(inode["blocs"], [0])
        self.assertIn("0-15 : #...............", carte)
        self.assertIn("16-17 : ..", carte)
        self.assertIn("inode 1 (nouveau.txt) -> blocs 0", carte)
        self.assertNotIn("ancien.txt", carte)

    def test_disque_et_fichier_vides(self):
        initialiser(self.image, nombre_blocs=17, taille_bloc=4, nombre_inodes=2)
        carte_vide = carte_blocs(self.image)
        creer_fichier(self.image, "vide.txt", "")

        carte = carte_blocs(self.image)
        explication = explication_fichier(self.image, "vide.txt")

        self.assertIn("0-15 : ................", carte_vide)
        self.assertIn("16-16 : .", carte_vide)
        self.assertIn("aucun inode occupe", carte_vide)
        self.assertIn("inode 1 (vide.txt) -> blocs aucun", carte)
        self.assertIn("Nombre de blocs : 0", explication)
        self.assertIn("Contenu UTF-8 assemble : ", explication)
        self.assertIn("Aucun bloc : fichier vide.", explication)
        self.assertIn("Capacite inutilisee du dernier bloc : 0 octet.", explication)

    def test_fichier_inconnu(self):
        initialiser(self.image, nombre_blocs=2, taille_bloc=4, nombre_inodes=1)
        with self.assertRaises(ValueError):
            explication_fichier(self.image, "absent.txt")


if __name__ == "__main__":
    unittest.main()
