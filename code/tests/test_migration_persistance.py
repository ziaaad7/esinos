"""Migration et garanties de persistance observées depuis l'API publique."""
import hashlib
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

CODE = Path(__file__).resolve().parents[1]
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from esinos.disque_binaire import MAGIC, geometrie
from esinos.filesystem import charger, creer_fichier, initialiser, lire_fichier
from esinos.filesystem import migrer_json, supprimer_fichier, lister_inodes
from esinos.filesystem import etat_disque, format_disque
from esinos.filesystem import reformater


class MigrationPersistanceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.folder = Path(self.temporary.name)
        self.image = self.folder / "nouveau.img"

    def tearDown(self):
        self.temporary.cleanup()

    def ancien_json(self):
        path = self.folder / "ancien.json"
        image = {
            "schema": "esinos-mini-filesystem", "version": 1,
            "block_size": 2, "block_count": 4, "max_inodes": 3,
            "inodes": [
                {"inode_id": 1, "name": "notes", "size": 3, "blocks": [0, 1]},
                {"inode_id": 3, "name": "vide", "size": 0, "blocks": []},
            ],
            "blocks": ["YcM=", "qQ==", None, None],
        }
        path.write_text(json.dumps(image), encoding="utf-8")
        return path

    def test_initialisation_est_binaire_et_geometrie_physique_exacte(self):
        state = initialiser(self.image, 4, 2, 3)
        data = self.image.read_bytes()
        self.assertTrue(data.startswith(MAGIC))
        self.assertEqual(len(data), geometrie(state)["taille_image"])
        self.assertEqual(format_disque(self.image), "binaire")
        self.assertEqual(etat_disque(self.image)["nombre_blocs"], 4)

    def test_migration_preserve_json_octets_utf8_geometrie_et_inodes(self):
        source = self.ancien_json()
        before = source.read_bytes()
        migrer_json(source, self.image)
        self.assertEqual(source.read_bytes(), before)
        self.assertEqual(format_disque(source), "json")
        self.assertEqual(charger(source), charger(self.image))
        self.assertEqual(lire_fichier(self.image, "notes"), "aé")
        self.assertEqual(lire_fichier(self.image, "vide"), "")
        self.assertIsNone(lister_inodes(self.image)[1])
        creer_fichier(self.image, "apres", "Z")
        self.assertEqual(source.read_bytes(), before)
        self.assertEqual(lire_fichier(self.image, "apres"), "Z")

    def test_migration_refuse_ecrasement_et_source_non_json(self):
        source = self.ancien_json()
        initialiser(self.image, 2, 4, 2)
        creer_fichier(self.image, "garde", "abc")
        before = self.image.read_bytes()
        with self.assertRaises(FileExistsError):
            migrer_json(source, self.image)
        self.assertEqual(self.image.read_bytes(), before)
        with self.assertRaises(ValueError):
            migrer_json(self.image, self.folder / "interdit.img")
        self.assertFalse((self.folder / "interdit.img").exists())

    def test_echec_publication_conserve_image_et_nettoie_temporaire(self):
        initialiser(self.image, 4, 4, 3)
        creer_fichier(self.image, "garde", "avant")
        before = self.image.read_bytes()
        with patch("esinos.filesystem.os.replace", side_effect=OSError("échec simulé")):
            with self.assertRaises(OSError):
                creer_fichier(self.image, "nouveau", "abc")
        self.assertEqual(self.image.read_bytes(), before)
        self.assertEqual(lire_fichier(self.image, "garde"), "avant")
        self.assertEqual(list(self.folder.glob("*.tmp")), [])
        self.assertEqual(list(self.folder.glob(".*.tmp")), [])

    def test_corruption_refusee_et_fichier_intact_apres_lecture(self):
        initialiser(self.image, 4, 4, 3)
        creer_fichier(self.image, "garde", "abc")
        raw = bytearray(self.image.read_bytes())
        raw[-1] ^= 1
        self.image.write_bytes(raw)
        before = hashlib.sha256(self.image.read_bytes()).hexdigest()
        with self.assertRaises(ValueError):
            charger(self.image)
        self.assertEqual(hashlib.sha256(self.image.read_bytes()).hexdigest(), before)

    def test_inodes_vides_limites_et_reutilisation(self):
        initialiser(self.image, 2, 4, 2)
        creer_fichier(self.image, "vide", "")
        creer_fichier(self.image, "plein", "12345678")
        self.assertEqual(etat_disque(self.image)["blocs_utilises"], 2)
        before = self.image.read_bytes()
        with self.assertRaises(ValueError):
            creer_fichier(self.image, "troisieme", "")
        self.assertEqual(self.image.read_bytes(), before)
        supprimer_fichier(self.image, "vide")
        inode = creer_fichier(self.image, "nouveau", "")
        self.assertEqual(inode["numero"], 1)
        self.assertEqual(lire_fichier(self.image, "plein"), "12345678")

    def test_geometries_geantes_refusees_avant_allocation(self):
        for blocks, size, inodes in ((10**20, 2, 2), (2, 10**20, 2), (2, 2, 10**20)):
            with self.subTest(blocks=blocks, size=size, inodes=inodes):
                with self.assertRaises(ValueError):
                    initialiser(self.image, blocks, size, inodes)
                self.assertFalse(self.image.exists())

    def test_migration_du_premier_atelier_hexadecimal(self):
        source = self.folder / "atelier.json"
        source.write_text(json.dumps({
            "taille_bloc": 2,
            "blocs": ["61c3", "a9", None],
            "inodes": [{"numero": 1, "nom": "accent", "taille": 3,
                        "blocs": [0, 1]}, None],
        }), encoding="utf-8")
        before = source.read_bytes()
        migrer_json(source, self.image)
        self.assertEqual(lire_fichier(self.image, "accent"), "aé")
        self.assertEqual(source.read_bytes(), before)

    def test_reformatage_garde_geometrie_et_permet_reutilisation(self):
        initialiser(self.image, 4, 4, 2)
        creer_fichier(self.image, "ancien", "abcdef")
        size = self.image.stat().st_size
        reformater(self.image)
        self.assertEqual(self.image.stat().st_size, size)
        self.assertEqual(format_disque(self.image), "binaire")
        self.assertEqual(lister_inodes(self.image), [None, None])
        self.assertEqual(etat_disque(self.image)["blocs_libres"], 4)
        inode = creer_fichier(self.image, "nouveau", "Z")
        self.assertEqual((inode["numero"], inode["blocs"]), (1, [0]))
        self.assertEqual(lire_fichier(self.image, "nouveau"), "Z")

    def test_noms_refuses_et_doublon_preservent_image(self):
        initialiser(self.image, 4, 4, 2)
        creer_fichier(self.image, "garde", "abc")
        before = self.image.read_bytes()
        for nom in ("", "../sortie", ".cache", "é", "nom avec espaces", "garde"):
            with self.subTest(nom=nom):
                with self.assertRaises(ValueError):
                    creer_fichier(self.image, nom, "X")
                self.assertEqual(self.image.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
