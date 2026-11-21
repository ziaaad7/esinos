"""Vérifie les opérations du bonus depuis le menu intégré."""
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
from esinos.filesystem import charger, initialiser, lire_fichier


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

    def test_creer_lire_table_et_suppression_annulee(self):
        sortie = self.lancer_menu([
            "1", "notes.txt", "aé", "4", "2", "notes.txt",
            "3", "notes.txt", "non", "0",
        ])
        self.assertIn("Table d'inodes", sortie)
        self.assertIn("notes.txt", sortie)
        self.assertIn("[0, 1]", sortie)
        self.assertIn("aé", sortie)
        self.assertIn("Action annulée.", sortie)
        self.assertEqual(lire_fichier(self.image, "notes.txt"), "aé")

    def test_suppression_confirmee_libere_inode_et_blocs(self):
        sortie = self.lancer_menu([
            "1", "sup.txt", "abcd", "3", "sup.txt", "oui", "4", "0",
        ])
        self.assertIn("Fichier supprimé. Ses blocs et son inode sont libres.", sortie)
        self.assertIn("libre", sortie)
        disque = charger(self.image)
        self.assertEqual(disque["blocs"], [None] * 4)
        self.assertEqual(disque["inodes"], [None] * 2)
        with self.assertRaises(ValueError):
            lire_fichier(self.image, "sup.txt")

    def test_erreur_de_nom_n_interrompt_pas_la_session(self):
        sortie = self.lancer_menu(["2", "absent.txt", "4", "0"])
        self.assertIn("Erreur :", sortie)
        self.assertIn("libre", sortie)


if __name__ == "__main__":
    unittest.main()
