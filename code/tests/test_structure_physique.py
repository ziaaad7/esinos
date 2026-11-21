"""Vérifie la disposition du disque avec des positions calculées à la main."""
import json
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
from esinos.filesystem import initialiser, creer_fichier, lire_fichier
from esinos.carte_disque import carte_blocs, explication_fichier


class StructurePhysiqueTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.image = self.folder / "disque.img"

    def tearDown(self):
        self.temp.cleanup()

    def test_positions_reelles_bitmap_inodes_repertoire_et_donnees(self):
        # Calcul indépendant : 4 blocs S + 1 B + 14 I + 18 R = 37 métadonnées.
        initialiser(self.image, 12, 16, 4)
        text = "Bonjour depuis le disque virtuel ESINOS."
        creer_fichier(self.image, "notes.txt", text)
        raw = self.image.read_bytes()
        self.assertEqual(len(raw), (37 + 12) * 16)
        self.assertEqual(raw[:8], b"ESINOSB1")
        self.assertEqual(raw[64], 0b11100000)  # données logiques 0, 1, 2
        self.assertEqual(raw[80], 1)  # premier inode actif
        self.assertEqual(int.from_bytes(raw[88:92], "big"), 0)
        self.assertEqual(int.from_bytes(raw[92:96], "big"), 1)
        self.assertEqual(int.from_bytes(raw[96:100], "big"), 2)
        self.assertEqual(int.from_bytes(raw[304:308], "big"), 1)
        self.assertEqual(raw[312:321], b"notes.txt")
        self.assertEqual(raw[592:632], text.encode("utf-8"))
        self.assertEqual(raw[632:640], b"\x00" * 8)

    def test_carte_et_suivi_distinguent_logique_et_physique(self):
        initialiser(self.image, 12, 16, 4)
        creer_fichier(self.image, "notes.txt", "Bonjour depuis le disque virtuel ESINOS.")
        before = self.image.read_bytes()
        map_text = carte_blocs(self.image)
        self.assertIn("S Superbloc : blocs 0 à 3", map_text)
        self.assertIn("I Inodes : blocs 5 à 18", map_text)
        self.assertIn("R Répertoire : blocs 19 à 36", map_text)
        self.assertIn("0-11 : ###.........", map_text)
        trace = explication_fichier(self.image, "notes.txt")
        self.assertIn("Logique 0 -> physique 37, position 592 octets", trace)
        self.assertEqual(self.image.read_bytes(), before)

    def test_octet_nul_utile_et_carte_condensee_avec_blocs_de_un_octet(self):
        initialiser(self.image, 4, 1, 2)
        creer_fichier(self.image, "texte", "A\x00é")
        self.assertEqual(lire_fichier(self.image, "texte"), "A\x00é")
        map_text = carte_blocs(self.image)
        self.assertIn("carte physique est condensée", map_text)
        self.assertIn("0-3 : ####", map_text)

    def test_menu_migration_propose_un_chemin_et_ouvre_la_copie(self):
        source = self.folder / "ancien.json"
        source.write_text(json.dumps({
            "schema": "esinos-mini-filesystem", "version": 1,
            "block_size": 4, "block_count": 2, "max_inodes": 2,
            "inodes": [{"inode_id": 1, "name": "accent", "size": 2, "blocks": [0]}],
            "blocks": ["w6k=", None],
        }), encoding="utf-8")
        before = source.read_bytes()
        output = StringIO()
        with patch.object(cli, "IMAGE", str(source)):
            with patch("builtins.input", side_effect=["10", "", "8", "0"]):
                with redirect_stdout(output):
                    cli.menu_disque()
        self.assertEqual(source.read_bytes(), before)
        self.assertEqual(lire_fichier(source.with_suffix(".img"), "accent"), "é")
        self.assertIn("STRUCTURE PHYSIQUE", output.getvalue())


if __name__ == "__main__":
    unittest.main()
