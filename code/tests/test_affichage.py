"""Tests des affichages texte et des explications CPU."""

import sys
import unittest
from pathlib import Path


CODE = Path(__file__).resolve().parents[1]
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from esinos.affichage import explication_cpu, gantt_texte, tableau_texte
from esinos.scheduler import ordonnancer


PROCESSUS = [
    {"nom": "P1", "arrivee": 0, "duree": 7, "priorite": 2},
    {"nom": "P2", "arrivee": 2, "duree": 4, "priorite": 1},
    {"nom": "P3", "arrivee": 4, "duree": 1, "priorite": 3},
    {"nom": "P4", "arrivee": 5, "duree": 4, "priorite": 2},
]


class GanttTexteTests(unittest.TestCase):
    def test_gantt_encadre_bornes_exactes_et_largeur_limitee(self):
        gantt = [
            ("P1", 0, 7),
            ("IDLE", 7, 1000000),
            ("ProcessusAvecUnNomVraimentBeaucoupTropLong", 1000000, 1000001),
        ]
        texte = gantt_texte(gantt, largeur=40)

        self.assertIn("GANTT", texte)
        self.assertIn("Cases de largeur fixe; bornes = durées exactes.", texte)
        self.assertIn("IDLE", texte)
        self.assertIn("0 -> 7", texte)
        self.assertIn("7 -> 1000000", texte)
        self.assertIn("1000000 -> 1000001", texte)
        self.assertIn("...", texte)
        self.assertIn("IDLE = CPU libre", texte)

        for ligne in texte.splitlines():
            if ligne.startswith("+") or ligne.startswith("|"):
                self.assertLessEqual(len(ligne), 40)

    def test_gantt_vide_et_tranches_invalides(self):
        self.assertEqual(gantt_texte([]), "GANTT : vide")
        with self.assertRaises(ValueError):
            gantt_texte([("P1", 0, 2), ("P2", 3, 4)])
        with self.assertRaises(ValueError):
            gantt_texte([("P1", 0, 0)])


class TableauTexteTests(unittest.TestCase):
    def test_tableau_aligne_et_affiche_none_par_un_tiret(self):
        texte = tableau_texte(
            ["PID", "Fin (CT)", "Victime"],
            [("P1", 7, None), ("ProcessusLong", 12, "P2")],
        )
        lignes = texte.splitlines()

        self.assertIn("| PID", texte)
        self.assertIn("|        7 |", texte)
        self.assertIn("| -", texte)
        self.assertTrue(lignes[0].startswith("+"))
        for ligne in lignes:
            self.assertEqual(len(ligne), len(lignes[0]))

    def test_tableau_refuse_une_ligne_incomplete(self):
        with self.assertRaises(ValueError):
            tableau_texte(["A", "B"], [("seulement une",)])


class ExplicationCpuTests(unittest.TestCase):
    def test_sjf_explique_le_choix_a_temps_sept(self):
        gantt, _ = ordonnancer(PROCESSUS, "sjf")
        phrases = explication_cpu(PROCESSUS, gantt, "sjf")

        self.assertEqual(len(phrases), len(gantt))
        self.assertIn("t=7", phrases[1])
        self.assertIn("SJF choisit P3", phrases[1])
        self.assertIn("durée 1", phrases[1])
        self.assertIn("P2, P3, P4", phrases[1])

    def test_fcfs_priorite_et_rr_expliquent_leur_regle(self):
        gantt_fcfs, _ = ordonnancer(PROCESSUS, "fcfs")
        phrases_fcfs = explication_cpu(PROCESSUS, gantt_fcfs, "fcfs")
        self.assertIn("FCFS choisit P1", phrases_fcfs[0])
        self.assertIn("arrivé le premier", phrases_fcfs[0])

        gantt_priorite, _ = ordonnancer(PROCESSUS, "priorite")
        phrases_priorite = explication_cpu(
            PROCESSUS, gantt_priorite, "priority"
        )
        self.assertIn("Priority choisit P2", phrases_priorite[1])
        self.assertIn("chiffre le plus petit", phrases_priorite[1])

        gantt_rr, _ = ordonnancer(PROCESSUS, "rr", 2)
        phrases_rr = explication_cpu(PROCESSUS, gantt_rr, "rr", 2)
        self.assertIn("reste 7 -> 5", phrases_rr[0])
        self.assertIn("Arrivées pendant la tranche : P2", phrases_rr[0])
        self.assertIn("File suivante", phrases_rr[0])

    def test_explication_decrit_un_cpu_idle(self):
        processus = [
            {"nom": "P1", "arrivee": 3, "duree": 1, "priorite": 0},
        ]
        gantt, _ = ordonnancer(processus, "fcfs")
        phrases = explication_cpu(processus, gantt, "fcfs")

        self.assertIn("IDLE", phrases[0])
        self.assertIn("P1 arrive à t=3", phrases[0])

    def test_explication_refuse_un_gantt_incoherent(self):
        processus = [
            {"nom": "P1", "arrivee": 0, "duree": 3, "priorite": 0},
            {"nom": "P2", "arrivee": 1, "duree": 2, "priorite": 0},
        ]
        gantt_faux = [("P1", 0, 2), ("P2", 2, 4), ("P1", 4, 5)]

        with self.assertRaises(ValueError):
            explication_cpu(processus, gantt_faux, "fcfs")


if __name__ == "__main__":
    unittest.main()

