"""Tests des explications textuelles construites depuis les traces mémoire."""

import sys
import unittest
from pathlib import Path


CODE = Path(__file__).resolve().parents[1]
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from esinos.memory import remplacer, traduire
from esinos.pedagogie import explications_remplacement, explications_traduction


class ExplicationsRemplacementTests(unittest.TestCase):
    def test_fifo_explique_la_page_la_plus_ancienne(self):
        pages = [1, 2, 3]
        _, trace = remplacer(pages, 2, "fifo")

        textes = explications_remplacement(pages, 2, "fifo", trace)

        self.assertEqual(len(textes), 3)
        self.assertIn("Référence 3", textes[2])
        self.assertIn("Avant : [1, 2]", textes[2])
        self.assertIn("FIFO choisit la page 1 du cadre 0", textes[2])
        self.assertIn("chargée à la référence 1", textes[2])
        self.assertIn("Après : [3, 2]", textes[2])

    def test_lru_rafraichit_un_hit_puis_evince_la_bonne_page(self):
        pages = [1, 2, 1, 3]
        _, trace = remplacer(pages, 2, "lru")

        textes = explications_remplacement(pages, 2, "lru", trace)

        self.assertIn("LRU rafraîchit la page 1", textes[2])
        self.assertIn("LRU choisit la page 2 du cadre 1", textes[3])
        self.assertIn("dernière fois à la référence 2", textes[3])

    def test_fifo_ne_change_pas_l_ordre_lors_d_un_hit(self):
        pages = [1, 2, 1]
        _, trace = remplacer(pages, 2, "fifo")

        textes = explications_remplacement(pages, 2, "fifo", trace)

        self.assertIn("FIFO ne change pas l'ordre", textes[2])
        self.assertIn("Avant : [1, 2]", textes[2])
        self.assertIn("Après : [1, 2]", textes[2])

    def test_optimal_explique_l_egalite_des_pages_jamais_reprises(self):
        pages = [1, 2, 3]
        _, trace = remplacer(pages, 2, "optimal")

        textes = explications_remplacement(pages, 2, "optimal", trace)

        self.assertIn("ne sont jamais reprises", textes[2])
        self.assertIn("Égalité", textes[2])
        self.assertIn("cadre 0", textes[2])
        self.assertIn("Après : [3, 2]", textes[2])


class ExplicationsTraductionTests(unittest.TestCase):
    def test_lru_rafraichit_un_hit_et_evince_l_entree_moins_recente(self):
        adresses = [0, 64, 0, 128]
        table = {0: 5, 1: 2, 2: 7}
        lignes, _ = traduire(adresses, 64, table, 2)

        textes = explications_traduction(adresses, 64, table, 2, lignes)

        self.assertIn("0 // 64 = 0", textes[0])
        self.assertIn("Hit TLB", textes[2])
        self.assertIn("LRU la rafraîchit", textes[2])
        self.assertIn("LRU évince la page 1 du cadre 2", textes[3])
        self.assertIn("TLB après : [p0→c5, p2→c7]", textes[3])

    def test_cadre_zero_et_page_absente_restent_distingues(self):
        adresses = [0, 64]
        table = {0: 0}
        lignes, _ = traduire(adresses, 64, table, 1)

        textes = explications_traduction(adresses, 64, table, 1, lignes)

        self.assertIn("cadre 0 est valide", textes[0])
        self.assertIn("Adresse physique = 0 × 64 + 0 = 0", textes[0])
        self.assertIn("page 1 est absente", textes[1])
        self.assertIn("cadre=None et adresse physique=None", textes[1])

    def test_capacite_zero_garde_un_cache_vide(self):
        adresses = [0]
        table = {0: 4}
        lignes, _ = traduire(adresses, 64, table, 0)

        textes = explications_traduction(adresses, 64, table, 0, lignes)

        self.assertIn("capacité est 0", textes[0])
        self.assertIn("TLB après : vide", textes[0])


if __name__ == "__main__":
    unittest.main()
