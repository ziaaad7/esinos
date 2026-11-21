"""Vérifie les entrées publiques, les sous-menus et leurs résultats."""
import re
import os
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

CODE = Path(__file__).resolve().parents[1]


def executer(*arguments, saisie=None):
    return subprocess.run(
        [sys.executable, "-B", "-m", "esinos", *arguments],
        cwd=CODE, input=saisie, encoding="utf-8", capture_output=True, timeout=15,
    )


def texte_simple(texte):
    return re.sub(r" +", " ", texte)


class CommandTests(unittest.TestCase):
    def test_console_utf8_meme_avec_un_encodage_initial_ascii(self):
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "ascii"
        resultat = subprocess.run(
            [sys.executable, "-B", "-m", "esinos", "demo"],
            cwd=CODE, env=env, encoding="utf-8", capture_output=True, timeout=15,
        )
        self.assertEqual(resultat.returncode, 0, resultat.stderr)
        self.assertIn("Déplacement", resultat.stdout)
        self.assertIn("Séjour moyen", resultat.stdout)

    def test_demonstration_complete(self):
        resultat = executer("demo")
        self.assertEqual(resultat.returncode, 0, resultat.stderr)
        texte = texte_simple(resultat.stdout)
        for attendu in ("FCFS | 4.75 | 8.75", "SJF | 4.00 | 8.00",
                        "RR | 5.00 | 9.00", "PRIORITE | 5.50 | 9.50",
                        "FIFO | 10 | 3", "LRU | 9 | 4", "OPTIMAL | 7 | 6",
                        "75 | 1 | 11 | 2 | 139 | hit", "1/8", "197.50 ns",
                        "notes.txt | 40 | [0, 1, 2]",
                        "Lecture : Bonjour depuis le disque virtuel ESINOS.",
                        "Après suppression :"):
            self.assertIn(attendu, texte)

    def test_menu_rr_redemande_un_quantum_valide(self):
        resultat = executer(saisie="1\n3\n0\n2\n0\n0\n")
        self.assertEqual(resultat.returncode, 0, resultat.stderr)
        self.assertIn("La valeur doit être au moins 1", resultat.stdout)
        self.assertIn("GANTT", resultat.stdout)
        self.assertIn("Attente moyenne : 5.00", resultat.stdout)
        self.assertNotIn("Expliqué", resultat.stdout)

    def test_saisie_cpu_guidee_et_comparaison_persistante(self):
        reponses = ["1", "6", "2",
                    "A", "3", "2", "2",
                    "B", "4", "1", "1",
                    "5", "2", "1", "0", "0"]
        resultat = executer(saisie="\n".join(reponses) + "\n")
        self.assertEqual(resultat.returncode, 0, resultat.stderr)
        texte = texte_simple(resultat.stdout)
        self.assertIn("IDLE", texte)
        self.assertIn("A | 3 | 2 | 2 | 5 | 0 | 2", texte)
        self.assertIn("B | 4 | 1 | 1 | 6 | 1 | 2", texte)
        self.assertIn("FCFS | 0.50 | 2.00", texte)

    def test_menu_memoire_compare_les_donnees_saisies(self):
        resultat = executer(saisie="2\n5\n1 2 1 3 1\n2\n4\n2\n0\n0\n")
        self.assertEqual(resultat.returncode, 0, resultat.stderr)
        texte = texte_simple(resultat.stdout)
        self.assertIn("FIFO | 4 | 1", texte)
        self.assertIn("LRU | 3 | 2", texte)
        self.assertIn("LRU : 3 défauts", texte)
        self.assertNotIn("Expliqué", texte)

    def test_menu_eat_refuse_nan_et_inf_avant_le_calcul(self):
        reponses = ["3", "2", "", "", "", "", "nan", "inf", "10", "",
                    "1", "0", "0"]
        resultat = executer(saisie="\n".join(reponses) + "\n")
        self.assertEqual(resultat.returncode, 0, resultat.stderr)
        self.assertEqual(resultat.stdout.count("Saisis un temps fini"), 2)
        self.assertIn("197.50 ns", resultat.stdout)
        self.assertIn("75", resultat.stdout)
        self.assertNotIn("Chemin hit", resultat.stdout)

    def test_aide_version_et_commandes_secondaires_retirees(self):
        aide = executer("--help")
        self.assertEqual(aide.returncode, 0)
        self.assertIn("demo", aide.stdout)
        self.assertIn("ESINOS 3.3.0", executer("--version").stdout)
        self.assertNotIn("--explain", aide.stdout)
        explain = executer("demo", "--explain")
        self.assertEqual(explain.returncode, 2)
        for commande in ("scheduler", "memory", "translate", "eat", "fs"):
            resultat = executer(commande)
            self.assertEqual(resultat.returncode, 2)
            self.assertNotIn("Traceback", resultat.stderr)



if __name__ == "__main__":
    unittest.main()
