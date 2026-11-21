"""Tests du modèle EAT qui inclut le traitement complet d'un défaut."""

import sys
import unittest
from pathlib import Path


CODE = Path(__file__).resolve().parents[1]
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from esinos.memory import calculer_eat, calculer_eat_defauts


class EatDefautsTests(unittest.TestCase):
    def test_extremes_et_temps_total_du_defaut(self):
        self.assertEqual(calculer_eat_defauts(0, 100, 1000), 100)
        self.assertEqual(calculer_eat_defauts(1, 100, 1000), 1000)
        self.assertNotEqual(calculer_eat_defauts(1, 100, 1000), 1100)

    def test_exemple_avec_un_millieme_de_defauts(self):
        resultat = calculer_eat_defauts(0.001, 100, 1000000)

        self.assertAlmostEqual(resultat, 1099.9)

    def test_ancien_modele_tlb_reste_identique(self):
        self.assertEqual(calculer_eat(1, 8, 10, 100), 197.5)

    def test_taux_invalide_est_refuse(self):
        valeurs = [-0.001, 1.001, float("nan"), float("inf"),
                   float("-inf"), True, "0.1", 10 ** 10000]

        for valeur in valeurs:
            with self.subTest(valeur=type(valeur).__name__):
                with self.assertRaises(ValueError):
                    calculer_eat_defauts(valeur)

    def test_temps_memoire_invalide_est_refuse(self):
        valeurs = [-1, float("nan"), float("inf"), False,
                   "100", 10 ** 10000]

        for valeur in valeurs:
            with self.subTest(valeur=type(valeur).__name__):
                with self.assertRaises(ValueError):
                    calculer_eat_defauts(0.1, valeur, 1000)

    def test_temps_de_defaut_invalide_est_refuse(self):
        valeurs = [-1, float("nan"), float("inf"), True,
                   "1000", 10 ** 10000]

        for valeur in valeurs:
            with self.subTest(valeur=type(valeur).__name__):
                with self.assertRaises(ValueError):
                    calculer_eat_defauts(0.1, 100, valeur)


if __name__ == "__main__":
    unittest.main()
