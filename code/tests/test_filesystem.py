"""Tests de persistance et de compatibilite du mini disque debutant."""

import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path


CODE = Path(__file__).resolve().parents[1]
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from esinos.filesystem import charger
from esinos.filesystem import creer_fichier
from esinos.filesystem import etat_disque
from esinos.filesystem import initialiser
from esinos.filesystem import lire_fichier
from esinos.filesystem import supprimer_fichier


class FileSystemTests(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.TemporaryDirectory()
        self.image = Path(self.dossier.name) / "disque.json"

    def tearDown(self):
        self.dossier.cleanup()

    def test_image_publiee_base64_est_lue_et_reouverte(self):
        image_publiee = {
            "schema": "esinos-mini-filesystem",
            "version": 1,
            "block_size": 4,
            "block_count": 3,
            "max_inodes": 2,
            "inodes": [
                {"inode_id": 1, "name": "ancien.txt", "size": 2,
                 "blocks": [0]},
            ],
            "blocks": ["w6k=", None, None],
        }
        self.image.write_text(json.dumps(image_publiee), encoding="utf-8")

        disque = charger(self.image)
        self.assertEqual(disque["inodes"][0]["nom"], "ancien.txt")
        self.assertEqual(lire_fichier(self.image, "ancien.txt"), "é")
        creer_fichier(self.image, "suite.txt", "abc")

        sauvegardee = json.loads(self.image.read_text(encoding="utf-8"))
        self.assertEqual(sauvegardee["schema"], "esinos-mini-filesystem")
        self.assertEqual(sauvegardee["version"], 1)
        self.assertEqual(lire_fichier(self.image, "ancien.txt"), "é")
        self.assertEqual(lire_fichier(self.image, "suite.txt"), "abc")

    def test_unicode_disque_plein_et_liberation_des_blocs(self):
        initialiser(self.image, nombre_blocs=3, taille_bloc=4, nombre_inodes=4)
        premier = creer_fichier(self.image, "accent.txt", "éé")
        creer_fichier(self.image, "deux.txt", "ABCD")
        creer_fichier(self.image, "trois.txt", "Z")
        self.assertEqual(premier["blocs"], [0])
        self.assertEqual(lire_fichier(self.image, "accent.txt"), "éé")

        with self.assertRaises(ValueError):
            creer_fichier(self.image, "plein.txt", "X")

        supprimer_fichier(self.image, "accent.txt")
        retour = creer_fichier(self.image, "retour.txt", "WXYZ")
        self.assertEqual(retour["blocs"], [0])
        self.assertEqual(etat_disque(self.image)["blocs_utilises"], 3)
        self.assertEqual(lire_fichier(self.image, "retour.txt"), "WXYZ")

    def test_initialiser_necrase_pas_une_image_existante(self):
        initialiser(self.image, nombre_blocs=4, taille_bloc=4, nombre_inodes=2)
        creer_fichier(self.image, "garde.txt", "conserver")
        avant = self.image.read_bytes()

        with self.assertRaises(FileExistsError):
            initialiser(self.image, nombre_blocs=1, taille_bloc=1, nombre_inodes=1)

        self.assertEqual(self.image.read_bytes(), avant)
        self.assertEqual(lire_fichier(self.image, "garde.txt"), "conserver")

    def test_deux_initialisations_concurrentes_ont_un_seul_gagnant(self):
        barriere = threading.Barrier(2)
        resultats = []
        verrou = threading.Lock()

        def essayer():
            barriere.wait()
            try:
                initialiser(self.image, nombre_blocs=5, taille_bloc=8,
                            nombre_inodes=3)
            except FileExistsError:
                resultat = "existe"
            except Exception as erreur:
                resultat = erreur
            else:
                resultat = "cree"
            with verrou:
                resultats.append(resultat)

        premier = threading.Thread(target=essayer)
        second = threading.Thread(target=essayer)
        premier.start()
        second.start()
        premier.join()
        second.join()

        self.assertCountEqual(resultats, ["cree", "existe"])
        disque = charger(self.image)
        self.assertEqual(len(disque["blocs"]), 5)
        self.assertEqual(len(disque["inodes"]), 3)
        self.assertEqual(list(self.image.parent.glob(".disque.json.*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
