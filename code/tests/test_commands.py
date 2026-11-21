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
            [sys.executable, "-B", "-m", "esinos", "translate", "--page-size", "64",
             "--page-table", "1:2", "--addresses", "70,75", "--explain"],
            cwd=CODE, env=env, encoding="utf-8", capture_output=True, timeout=15,
        )
        self.assertEqual(resultat.returncode, 0, resultat.stderr)
        self.assertIn("déplacement", resultat.stdout)
        self.assertIn("p1→c2", resultat.stdout)

    def test_demonstration_complete(self):
        resultat = executer("demo")
        self.assertEqual(resultat.returncode, 0, resultat.stderr)
        texte = texte_simple(resultat.stdout)
        for attendu in ("FCFS | 4.75 | 8.75", "SJF | 4.00 | 8.00",
                        "RR | 5.00 | 9.00", "PRIORITE | 5.50 | 9.50",
                        "FIFO | 10 | 3", "LRU | 9 | 4", "OPTIMAL | 7 | 6",
                        "75 | 1 | 11 | 2 | 139 | hit", "1/8", "197.50 ns",
                        "notes.txt | 40 | [0, 1, 2]",
                        "0-11 : ###.........", "0-11 : ............"):
            self.assertIn(attendu, texte)

    def test_commandes_cpu_et_memoire(self):
        cpu = executer("scheduler", "--algorithm", "rr", "--quantum", "2",
                       "--processes", "A:0:3,B:1:2,C:2:1")
        self.assertEqual(cpu.returncode, 0, cpu.stderr)
        self.assertIn("| A ", cpu.stdout)
        for bornes in ("0 -> 2", "2 -> 4", "4 -> 5", "5 -> 6"):
            self.assertIn(bornes, cpu.stdout)
        self.assertIn("Attente moyenne : 2.00", cpu.stdout)
        priorite = executer("scheduler", "--algorithm", "priorite",
                            "--processes", "A:0:1:2,B:0:1:1")
        self.assertEqual(priorite.returncode, 0, priorite.stderr)
        self.assertIn("PRIORITE", priorite.stdout)
        memoire = executer("memory", "--references", "1,2,1,3,1",
                           "--frames", "2", "--algorithm", "lru")
        self.assertEqual(memoire.returncode, 0, memoire.stderr)
        self.assertIn("LRU : 3", memoire.stdout)

    def test_tlb_desactive_et_page_absente(self):
        resultat = executer("translate", "--addresses", "17,19,55",
                            "--page-size", "16", "--page-table", "1:0",
                            "--tlb-size", "0", "--explain")
        self.assertEqual(resultat.returncode, 0, resultat.stderr)
        self.assertIn("17 | 1 | 1 | 0 | 1 | miss", texte_simple(resultat.stdout))
        self.assertIn("défaut de page", resultat.stdout)
        self.assertIn("0/3", resultat.stdout)
        self.assertIn("210.00", resultat.stdout)
        self.assertIn("désactivé", resultat.stdout)

    def test_erreurs_recuperables(self):
        for valeur in ("nan", "inf", "-inf"):
            resultat = executer("translate", "--addresses", "1", "--page-size", "4",
                                "--page-table", "0:0", "--tlb-time=" + valeur)
            self.assertEqual(resultat.returncode, 2)
            self.assertIn("Erreur", resultat.stderr)
            self.assertNotIn("Traceback", resultat.stderr)
        for arguments in [
            ("scheduler", "--algorithm", "rr", "--processes", "P:0:1"),
            ("memory", "--references", "1,-2", "--frames", "3",
             "--algorithm", "fifo"),
        ]:
            resultat = executer(*arguments)
            self.assertEqual(resultat.returncode, 2)
            self.assertIn("Erreur", resultat.stderr)
            self.assertNotIn("Traceback", resultat.stderr)

    def test_menu_rr_redemande_un_quantum_valide(self):
        resultat = executer(saisie="1\n3\n0\n2\n1\n0\n0\n")
        self.assertEqual(resultat.returncode, 0, resultat.stderr)
        self.assertIn("La valeur doit être au moins 1", resultat.stdout)
        self.assertIn("GANTT", resultat.stdout)
        self.assertIn("Attente moyenne : 5.00", resultat.stdout)

    def test_saisie_cpu_guidee_et_comparaison_persistante(self):
        reponses = ["1", "6", "2",
                    "A", "3", "2", "2",
                    "B", "4", "1", "1",
                    "5", "2", "1", "1", "0", "0"]
        resultat = executer(saisie="\n".join(reponses) + "\n")
        self.assertEqual(resultat.returncode, 0, resultat.stderr)
        texte = texte_simple(resultat.stdout)
        self.assertIn("IDLE", texte)
        self.assertIn("3 -> 5", texte)
        self.assertIn("B | 4 | 1 | 1 | 6 | 1 | 2", texte)
        self.assertIn("FCFS | 0.50 | 2.00", texte)

    def test_mode_pas_a_pas_peut_continuer_et_revenir(self):
        resultat = executer(saisie="1\n3\n2\n3\n\nt\n0\n0\n")
        self.assertEqual(resultat.returncode, 0, resultat.stderr)
        self.assertIn("File suivante", resultat.stdout)
        self.assertIn("reste 7 -> 5", resultat.stdout)
        self.assertEqual(resultat.stdout.count("Entrée : suite"), 2)
        arret = executer(saisie="1\n1\n3\n0\n4\n1\n0\n0\n")
        self.assertEqual(arret.returncode, 0, arret.stderr)
        self.assertEqual(arret.stdout.count("GANTT"), 1)
        self.assertIn("Attente moyenne : 5.50", arret.stdout)

    def test_menu_memoire_compare_les_donnees_saisies(self):
        resultat = executer(saisie="2\n5\n1 2 1 3 1\n2\n4\n2\n2\n0\n0\n")
        self.assertEqual(resultat.returncode, 0, resultat.stderr)
        texte = texte_simple(resultat.stdout)
        self.assertIn("FIFO | 4 | 1", texte)
        self.assertIn("LRU | 3 | 2", texte)
        self.assertIn("LRU : 3 défauts", texte)
        self.assertIn("la page 2", texte)

    def test_menu_eat_refuse_nan_et_inf_avant_le_calcul(self):
        reponses = ["3", "2", "", "", "", "", "nan", "inf", "10", "",
                    "1", "2", "0", "0"]
        resultat = executer(saisie="\n".join(reponses) + "\n")
        self.assertEqual(resultat.returncode, 0, resultat.stderr)
        self.assertEqual(resultat.stdout.count("Saisis un temps fini"), 2)
        self.assertIn("197.50 ns", resultat.stdout)
        self.assertIn("75", resultat.stdout)
        self.assertIn("Chemin hit : 10 + 100 = 110", resultat.stdout)

    def test_demonstration_expliquee_reste_automatique(self):
        resultat = executer("demo", "--explain")
        self.assertEqual(resultat.returncode, 0, resultat.stderr)
        self.assertIn("File suivante", resultat.stdout)
        self.assertIn("FIFO choisit la page 7", resultat.stdout)
        self.assertIn("TLB avant", resultat.stdout)
        self.assertIn("197.50 ns", resultat.stdout)
        self.assertNotIn("Entrée : suite", resultat.stdout)

    def test_fichiers_entre_plusieurs_commandes(self):
        with TemporaryDirectory() as dossier:
            image = str(Path(dossier) / "disque.json")
            base = ("fs", "--disk", image)
            creation = executer(*base, "--blocks", "4", "--block-size", "2",
                               "--inodes", "2", "init")
            self.assertEqual(creation.returncode, 0, creation.stderr)
            self.assertEqual(executer(*base, "create", "notes", "aé").returncode, 0)
            self.assertEqual(executer(*base, "read", "notes").stdout.strip(), "aé")
            self.assertIn("[0, 1]", executer(*base, "inodes").stdout)
            self.assertIn("0-3 : ##..", executer(*base, "map").stdout)
            parcours = executer(*base, "explain", "notes")
            self.assertEqual(parcours.returncode, 0, parcours.stderr)
            self.assertIn("aé", parcours.stdout)
            self.assertIn("Bloc 1 : 1/2", parcours.stdout)
            self.assertEqual(executer(*base, "init").returncode, 2)
            self.assertEqual(executer(*base, "read", "notes").stdout.strip(), "aé")
            self.assertEqual(executer(*base, "delete", "notes").returncode, 0)
            self.assertIn("libre", executer(*base, "inodes").stdout)
            self.assertIn("0-3 : ....", executer(*base, "map").stdout)


if __name__ == "__main__":
    unittest.main()
