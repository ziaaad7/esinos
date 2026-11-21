"""Tests publics des commandes ajoutées dans ESINOS 3."""

import base64
import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


CODE = Path(__file__).resolve().parents[1]


def executer(*arguments, saisie=None):
    """Lance uniquement l'interface publique, dans un processus séparé."""
    return subprocess.run(
        [sys.executable, "-B", "-m", "esinos", *arguments],
        cwd=CODE,
        input=saisie,
        encoding="utf-8",
        capture_output=True,
        timeout=15,
    )


def verifier_erreur(test, resultat):
    """Vérifie une erreur CLI propre, sans détails internes."""
    test.assertEqual(resultat.returncode, 2)
    test.assertIn("Erreur", resultat.stderr)
    test.assertNotIn("Traceback", resultat.stdout + resultat.stderr)


class CommandesV3Tests(unittest.TestCase):
    def test_eat_accepte_le_scenario_et_les_limites(self):
        exemple = executer(
            "eat", "--fault-rate", "0.001", "--memory-time", "100",
            "--fault-time", "1000000",
        )
        self.assertEqual(exemple.returncode, 0, exemple.stderr)
        self.assertIn("1099.90 ns", exemple.stdout)
        self.assertIn("tout le traitement du défaut", exemple.stdout)

        sans_defaut = executer(
            "eat", "--fault-rate", "0", "--memory-time", "100",
            "--fault-time", "1000000",
        )
        self.assertEqual(sans_defaut.returncode, 0, sans_defaut.stderr)
        self.assertIn("100.00 ns", sans_defaut.stdout)

        toujours_defaut = executer(
            "eat", "--fault-rate", "1", "--memory-time", "100",
            "--fault-time", "1000000",
        )
        self.assertEqual(toujours_defaut.returncode, 0, toujours_defaut.stderr)
        self.assertIn("1000000.00 ns", toujours_defaut.stdout)

    def test_eat_refuse_les_taux_non_finis_et_hors_bornes(self):
        for taux in ("nan", "inf", "-inf", "1.001", "-0.001"):
            with self.subTest(taux=taux):
                resultat = executer("eat", "--fault-rate=" + taux)
                verifier_erreur(self, resultat)

        for arguments in (
            ("--fault-rate", "0.1", "--memory-time", "nan"),
            ("--fault-rate", "0.1", "--fault-time", "inf"),
        ):
            with self.subTest(arguments=arguments):
                resultat = executer("eat", *arguments)
                verifier_erreur(self, resultat)

    def test_menu_option_six_redemande_puis_revient_au_menu(self):
        resultat = executer(
            saisie="6\n1.2\nnan\n0.001\n\n\n0\n",
        )

        self.assertEqual(resultat.returncode, 0, resultat.stderr)
        self.assertIn("Le taux doit être compris entre 0 et 1.", resultat.stdout)
        self.assertIn("Saisis un temps fini, positif ou nul.", resultat.stdout)
        self.assertIn("1099.90 ns", resultat.stdout)
        self.assertNotIn("Traceback", resultat.stdout + resultat.stderr)

    def test_migration_cli_conserve_json_et_refuse_ecrasement(self):
        with TemporaryDirectory() as dossier:
            source = Path(dossier) / "ancien.json"
            destination = Path(dossier) / "nouveau.img"
            ancien = {
                "schema": "esinos-mini-filesystem",
                "version": 1,
                "block_size": 4,
                "block_count": 2,
                "max_inodes": 2,
                "inodes": [
                    {"inode_id": 1, "name": "notes.txt", "size": 2,
                     "blocks": [0]},
                ],
                "blocks": [base64.b64encode("é".encode("utf-8")).decode("ascii"),
                           None],
            }
            source.write_text(json.dumps(ancien), encoding="utf-8")
            octets_source = source.read_bytes()

            migration = executer("fs", "--disk", str(source), "migrate",
                                 str(destination))
            self.assertEqual(migration.returncode, 0, migration.stderr)
            self.assertIn("Copie binaire créée", migration.stdout)
            self.assertTrue(destination.exists())
            self.assertEqual(source.read_bytes(), octets_source)

            lecture = executer("fs", "--disk", str(destination), "read", "notes.txt")
            self.assertEqual(lecture.returncode, 0, lecture.stderr)
            self.assertEqual(lecture.stdout.strip(), "é")
            self.assertEqual(source.read_bytes(), octets_source)

            octets_destination = destination.read_bytes()
            refus = executer("fs", "--disk", str(source), "migrate",
                             str(destination))
            verifier_erreur(self, refus)
            self.assertEqual(source.read_bytes(), octets_source)
            self.assertEqual(destination.read_bytes(), octets_destination)


if __name__ == "__main__":
    unittest.main()
