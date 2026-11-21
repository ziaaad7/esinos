"""Tests des affichages texte CPU."""

import sys
import unittest
from pathlib import Path


CODE = Path(__file__).resolve().parents[1]
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from esinos.affichage import gantt_texte, tableau_texte


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


if __name__ == "__main__":
    unittest.main()

