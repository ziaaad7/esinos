"""Tests simples des algorithmes presentes dans ESINOS debutant."""

import sys
import unittest
from pathlib import Path


CODE = Path(__file__).resolve().parents[1]
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from esinos.cli import lire_processus
from esinos.memory import calculer_eat, remplacer, traduire
from esinos.scheduler import ordonnancer


PROCESSUS_DEMO = [
    {"nom": "P1", "arrivee": 0, "duree": 7, "priorite": 2},
    {"nom": "P2", "arrivee": 2, "duree": 4, "priorite": 1},
    {"nom": "P3", "arrivee": 4, "duree": 1, "priorite": 3},
    {"nom": "P4", "arrivee": 5, "duree": 4, "priorite": 2},
]


class SchedulerTests(unittest.TestCase):
    def test_quatre_gantt_de_la_demonstration(self):
        attendus = {
            "fcfs": [
                ("P1", 0, 7), ("P2", 7, 11),
                ("P3", 11, 12), ("P4", 12, 16),
            ],
            "sjf": [
                ("P1", 0, 7), ("P3", 7, 8),
                ("P2", 8, 12), ("P4", 12, 16),
            ],
            "rr": [
                ("P1", 0, 2), ("P2", 2, 4), ("P1", 4, 6),
                ("P3", 6, 7), ("P2", 7, 9), ("P4", 9, 11),
                ("P1", 11, 13), ("P4", 13, 15), ("P1", 15, 16),
            ],
            "priorite": [
                ("P1", 0, 7), ("P2", 7, 11),
                ("P4", 11, 15), ("P3", 15, 16),
            ],
        }

        for algorithme in attendus:
            with self.subTest(algorithme=algorithme):
                gantt, lignes = ordonnancer(PROCESSUS_DEMO, algorithme, 2)
                self.assertEqual(gantt, attendus[algorithme])
                self.assertEqual(len(lignes), 4)

    def test_mesures_et_alias_priority(self):
        _, lignes = ordonnancer(PROCESSUS_DEMO, "fcfs")
        self.assertEqual(
            lignes,
            [
                ("P1", 0, 7, 2, 7, 0, 7),
                ("P2", 2, 4, 1, 11, 5, 9),
                ("P3", 4, 1, 3, 12, 7, 8),
                ("P4", 5, 4, 2, 16, 7, 11),
            ],
        )
        gantt_francais, _ = ordonnancer(PROCESSUS_DEMO, "priorite")
        gantt_anglais, _ = ordonnancer(PROCESSUS_DEMO, "priority")
        self.assertEqual(gantt_anglais, gantt_francais)

    def test_rr_place_l_arrivee_de_fin_avant_la_reinsertion(self):
        processus = [
            {"nom": "P1", "arrivee": 0, "duree": 3, "priorite": 0},
            {"nom": "P2", "arrivee": 1, "duree": 2, "priorite": 0},
            {"nom": "P3", "arrivee": 2, "duree": 1, "priorite": 0},
        ]
        gantt, _ = ordonnancer(processus, "rr", 2)
        self.assertEqual(
            gantt,
            [("P1", 0, 2), ("P2", 2, 4),
             ("P3", 4, 5), ("P1", 5, 6)],
        )

    def test_idle_est_visible_avant_une_arrivee_tardive(self):
        processus = [
            {"nom": "P1", "arrivee": 2, "duree": 2, "priorite": 0},
            {"nom": "P2", "arrivee": 4, "duree": 1, "priorite": 0},
        ]
        gantt, lignes = ordonnancer(processus, "fcfs")
        self.assertEqual(gantt, [("IDLE", 0, 2), ("P1", 2, 4),
                                 ("P2", 4, 5)])
        self.assertEqual(lignes[0][-3:], (4, 0, 2))

    def test_entrees_invalides(self):
        cas = [
            ([], "fcfs", 2),
            ([{"nom": "P", "arrivee": -1, "duree": 1, "priorite": 0}],
             "fcfs", 2),
            ([{"nom": "P", "arrivee": 0, "duree": 0, "priorite": 0}],
             "fcfs", 2),
            ([{"nom": "IDLE", "arrivee": 0, "duree": 1, "priorite": 0}],
             "fcfs", 2),
            (PROCESSUS_DEMO, "inconnu", 2),
            (PROCESSUS_DEMO, "rr", 0),
        ]
        for processus, algorithme, quantum in cas:
            with self.subTest(algorithme=algorithme, quantum=quantum):
                with self.assertRaises(ValueError):
                    ordonnancer(processus, algorithme, quantum)

    def test_saisie_optionnelle_sans_priorite(self):
        processus = lire_processus("P1:0:3,P2:1:2:7")
        self.assertEqual(
            processus,
            [
                {"nom": "P1", "arrivee": 0, "duree": 3, "priorite": 0},
                {"nom": "P2", "arrivee": 1, "duree": 2, "priorite": 7},
            ],
        )


class MemoryTests(unittest.TestCase):
    def test_remplacement_de_la_demonstration(self):
        pages = [7, 0, 1, 2, 0, 3, 0, 4, 2, 3, 0, 3, 2]
        fifo, _ = remplacer(pages, 3, "fifo")
        lru, _ = remplacer(pages, 3, "lru")
        optimal, _ = remplacer(pages, 3, "optimal")
        self.assertEqual((fifo, lru, optimal), (10, 9, 7))

    def test_traduction_tlb_et_eat_de_la_demonstration(self):
        adresses = [5, 70, 75, 130, 5, 195, 70, 260]
        table = {0: 5, 1: 2, 2: 7, 3: 1}
        lignes, hits = traduire(adresses, 64, table, 2)
        self.assertEqual(hits, 1)
        self.assertEqual(lignes[2], (75, 1, 11, 2, 139, True))
        self.assertIsNone(lignes[-1][4])
        self.assertEqual(calculer_eat(hits, len(lignes)), 197.5)


if __name__ == "__main__":
    unittest.main()
