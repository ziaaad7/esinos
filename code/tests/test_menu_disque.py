"""Tests du sous-menu disque : carte, suivi et confirmations."""

import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


CODE = Path(__file__).resolve().parents[1]
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from esinos import cli
from esinos.carte_disque import carte_blocs
from esinos.filesystem import initialiser, lire_fichier


class MenuDisqueTests(unittest.TestCase):
    def setUp(self):
        self.dossier = TemporaryDirectory()
        self.image = Path(self.dossier.name) / "menu.disk.json"
        initialiser(self.image, nombre_blocs=4, taille_bloc=2, nombre_inodes=2)

    def tearDown(self):
        self.dossier.cleanup()

    def lancer_menu(self, reponses):
        sortie = StringIO()
        with patch.object(cli, "IMAGE", str(self.image)):
            with patch("builtins.input", side_effect=reponses):
                with redirect_stdout(sortie):
                    cli.menu_disque()
        return sortie.getvalue()

    def test_options_8_et_9_et_annulations_preservent_un_fichier_utf8(self):
        sortie = self.lancer_menu([
            "1", "notes.txt", "aé",
            "8",
            "9", "notes.txt",
            "3", "notes.txt", "non",
            "7", "non",
            "8",
            "2", "notes.txt",
            "0",
        ])

        self.assertIn("8 Carte des blocs | 9 Suivre un fichier", sortie)
        self.assertIn("CARTE DES BLOCS", sortie)
        self.assertIn("0-3 : ##..", sortie)
        self.assertIn("FICHIER : notes.txt", sortie)
        self.assertIn("Contenu UTF-8 assemble : aé", sortie)
        self.assertEqual(sortie.count("Action annulée."), 2)
        self.assertNotIn("Fichier supprimé.", sortie)
        self.assertNotIn("Disque reformaté.", sortie)
        self.assertEqual(lire_fichier(self.image, "notes.txt"), "aé")

    def test_suppression_confirmee_libere_la_carte_des_blocs(self):
        sortie = self.lancer_menu([
            "1", "sup.txt", "abcd",
            "3", "sup.txt", "oui",
            "8",
            "0",
        ])

        self.assertIn("Fichier supprimé. Ses blocs et son inode sont libres.", sortie)
        self.assertNotIn("Action annulée.", sortie)
        self.assertIn("0-3 : ....", sortie)
        self.assertIn("0-3 : ....", carte_blocs(self.image))
        with self.assertRaises(ValueError):
            lire_fichier(self.image, "sup.txt")


if __name__ == "__main__":
    unittest.main()

