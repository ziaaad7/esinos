"""Vérifie les commandes publiques et la gestion des saisies."""

import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

CODE = Path(__file__).resolve().parents[1]


def executer(*arguments, saisie=None):
    return subprocess.run(
        [sys.executable, "-B", "-m", "esinos", *arguments],
        cwd=CODE, input=saisie, text=True, capture_output=True,
    )


class CommandTests(unittest.TestCase):
    def test_demonstration_complete(self):
        resultat = executer("demo")
        self.assertEqual(resultat.returncode, 0, resultat.stderr)
        for texte in ("4.75", "8.75", "4.00", "8.00", "5.00", "9.00",
                      "5.50", "9.50", "FIFO : 10", "LRU : 9", "OPTIMAL : 7",
                      "75 | 1 | 11 | 2 | 139 | hit", "1/8", "197.50 ns",
                      "notes.txt | 40 | [0, 1, 2]"):
            self.assertIn(texte, resultat.stdout)

    def test_commandes_cpu_et_memoire(self):
        cpu = executer("scheduler", "--algorithm", "rr", "--quantum", "2",
                       "--processes", "A:0:3,B:1:2,C:2:1")
        self.assertEqual(cpu.returncode, 0, cpu.stderr)
        self.assertIn("A [0-2] -> B [2-4] -> C [4-5] -> A [5-6]", cpu.stdout)
        memoire = executer("memory", "--references", "1,2,1,3,1",
                           "--frames", "2", "--algorithm", "lru")
        self.assertEqual(memoire.returncode, 0, memoire.stderr)
        self.assertIn("LRU : 3", memoire.stdout)

    def test_tlb_desactive_et_page_absente(self):
        resultat = executer("translate", "--addresses", "17,19,55",
                            "--page-size", "16", "--page-table", "1:0",
                            "--tlb-size", "0")
        self.assertEqual(resultat.returncode, 0, resultat.stderr)
        self.assertIn("17 | 1 | 1 | 0 | 1 | miss", resultat.stdout)
        self.assertIn("défaut de page", resultat.stdout)
        self.assertIn("0/3", resultat.stdout)
        self.assertIn("210.00", resultat.stdout)

    def test_erreurs_recuperables(self):
        for arguments in [
            ("scheduler", "--algorithm", "rr", "--processes", "P:0:1"),
            ("translate", "--addresses", "1", "--page-size", "4",
             "--page-table", "0:0", "--tlb-time", "nan"),
            ("memory", "--references", "1,-2", "--frames", "3",
             "--algorithm", "fifo"),
        ]:
            resultat = executer(*arguments)
            self.assertEqual(resultat.returncode, 2)
            self.assertIn("Erreur", resultat.stderr)
            self.assertNotIn("Traceback", resultat.stderr)

    def test_menu_choix_numerique_et_saisie_invalide(self):
        resultat = executer(saisie="1\n\n3\n2\n2\n\nabc\n1\n\n1\n0\n")
        self.assertEqual(resultat.returncode, 0, resultat.stderr)
        self.assertIn("RR", resultat.stdout)
        self.assertIn("Erreur", resultat.stdout)
        self.assertIn("FCFS", resultat.stdout)

    def test_fichiers_entre_plusieurs_commandes(self):
        with TemporaryDirectory() as dossier:
            image = str(Path(dossier) / "disque.json")
            base = ("fs", "--disk", image)
            creation = executer(*base, "--blocks", "4", "--block-size", "2",
                               "--inodes", "2", "init")
            self.assertEqual(creation.returncode, 0, creation.stderr)
            self.assertEqual(executer(*base, "create", "notes", "aé").returncode, 0)
            lecture = executer(*base, "read", "notes")
            self.assertEqual(lecture.stdout.strip(), "aé")
            self.assertIn("[0, 1]", executer(*base, "inodes").stdout)
            self.assertEqual(executer(*base, "init").returncode, 2)
            self.assertEqual(executer(*base, "read", "notes").stdout.strip(), "aé")
            self.assertEqual(executer(*base, "delete", "notes").returncode, 0)
            self.assertIn("libre", executer(*base, "inodes").stdout)


if __name__ == "__main__":
    unittest.main()
