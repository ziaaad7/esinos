"""Proprietes verifiees par des modeles de reference independants.

Ces tests ne reutilisent pas les boucles des modules testes. Ils comparent
plutot les resultats a de petits simulateurs ecrits ici pour rendre visibles
les conventions ESINOS : arrivees a la frontiere RR, egalites et TLB LRU.
"""

import itertools
import math
import sys
import unittest
from pathlib import Path


CODE = Path(__file__).resolve().parents[1]
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from esinos.memory import calculer_eat, calculer_eat_defauts, remplacer, traduire
from esinos.scheduler import ordonnancer


def _faire_lignes(processus, gantt):
    """Reconstruit les mesures uniquement a partir d'un Gantt."""
    fins = {}
    for nom, debut, fin in gantt:
        if nom != "IDLE":
            fins[nom] = fin

    lignes = []
    for processus_un in processus:
        nom = processus_un["nom"]
        arrivee = processus_un["arrivee"]
        duree = processus_un["duree"]
        priorite = processus_un["priorite"]
        fin = fins[nom]
        sejour = fin - arrivee
        attente = sejour - duree
        lignes.append((nom, arrivee, duree, priorite, fin, attente, sejour))
    return lignes


def _executer_un_a_un(gantt, nom, horloge, duree):
    """Avance une tranche un tick a la fois sans consulter le programme."""
    debut = horloge
    reste = duree
    while reste > 0:
        horloge += 1
        reste -= 1
    gantt.append((nom, debut, horloge))
    return horloge


def oracle_ordonnancement(processus, algorithme, quantum=2):
    """Petit ordonnanceur de reference, volontairement distinct du module."""
    ordre = []
    for processus_un in processus:
        ordre.append(
            (
                processus_un["arrivee"],
                processus_un["nom"],
                processus_un["duree"],
                processus_un["priorite"],
            )
        )
    ordre.sort()
    gantt = []
    horloge = 0

    if algorithme == "fcfs":
        for arrivee, nom, duree, priorite in ordre:
            if arrivee > horloge:
                gantt.append(("IDLE", horloge, arrivee))
                horloge = arrivee
            horloge = _executer_un_a_un(gantt, nom, horloge, duree)

    elif algorithme in ("sjf", "priorite"):
        a_faire = ordre.copy()
        while a_faire:
            pret = []
            for processus_un in a_faire:
                if processus_un[0] <= horloge:
                    pret.append(processus_un)

            if not pret:
                arrivee = a_faire[0][0]
                gantt.append(("IDLE", horloge, arrivee))
                horloge = arrivee
                continue

            choix = pret[0]
            for candidat in pret[1:]:
                if algorithme == "sjf":
                    cle_choix = (choix[2], choix[0], choix[1])
                    cle_candidat = (candidat[2], candidat[0], candidat[1])
                else:
                    cle_choix = (choix[3], choix[0], choix[1])
                    cle_candidat = (candidat[3], candidat[0], candidat[1])
                if cle_candidat < cle_choix:
                    choix = candidat

            a_faire.remove(choix)
            horloge = _executer_un_a_un(gantt, choix[1], horloge, choix[2])

    else:
        reste = {}
        for arrivee, nom, duree, priorite in ordre:
            reste[nom] = duree

        file = []
        suivant = 0
        while suivant < len(ordre) or file:
            if not file:
                arrivee = ordre[suivant][0]
                if arrivee > horloge:
                    gantt.append(("IDLE", horloge, arrivee))
                    horloge = arrivee
                while suivant < len(ordre) and ordre[suivant][0] <= horloge:
                    file.append(ordre[suivant][1])
                    suivant += 1

            nom = file.pop(0)
            debut = horloge
            ticks = 0
            while ticks < quantum and reste[nom] > 0:
                reste[nom] -= 1
                horloge += 1
                ticks += 1
            gantt.append((nom, debut, horloge))

            while suivant < len(ordre) and ordre[suivant][0] <= horloge:
                file.append(ordre[suivant][1])
                suivant += 1
            if reste[nom] > 0:
                file.append(nom)

    return gantt, _faire_lignes(processus, gantt)


def oracle_remplacement(pages, nombre_cadres, algorithme):
    """Simule FIFO, LRU et Optimal sans appeler les fonctions ESINOS."""
    cadres = [None] * nombre_cadres
    ordre_fifo = []
    dernier_usage = {}
    trace = []
    defauts = 0

    for indice, page in enumerate(pages):
        hit = page in cadres
        victime = None

        if hit:
            dernier_usage[page] = indice
        else:
            defauts += 1
            if None in cadres:
                numero = cadres.index(None)
            elif algorithme == "fifo":
                numero = ordre_fifo.pop(0)
            elif algorithme == "lru":
                numero = 0
                for candidat in range(1, len(cadres)):
                    if dernier_usage[cadres[candidat]] < dernier_usage[cadres[numero]]:
                        numero = candidat
            else:
                numero = 0
                plus_loin = -1
                for candidat in range(len(cadres)):
                    prochaine = len(pages)
                    for futur in range(indice + 1, len(pages)):
                        if pages[futur] == cadres[candidat]:
                            prochaine = futur
                            break
                    if prochaine > plus_loin:
                        plus_loin = prochaine
                        numero = candidat

            victime = cadres[numero]
            if victime is not None:
                del dernier_usage[victime]
            cadres[numero] = page
            dernier_usage[page] = indice
            if algorithme == "fifo":
                ordre_fifo.append(numero)

        trace.append((page, hit, victime, cadres.copy()))

    return defauts, trace


def oracle_traduction(adresses, taille_page, table_pages, capacite_tlb):
    """Modele LRU minimal du TLB, incluant les pages non mappees."""
    tlb = {}
    ordre = []
    lignes = []
    hits = 0

    for adresse in adresses:
        page = adresse // taille_page
        deplacement = adresse % taille_page
        cadre = None
        hit = False

        if capacite_tlb > 0 and page in tlb:
            cadre = tlb[page]
            hit = True
            hits += 1
            ordre.remove(page)
            ordre.append(page)
        elif page in table_pages:
            cadre = table_pages[page]
            if capacite_tlb > 0:
                if len(ordre) == capacite_tlb:
                    ancienne_page = ordre.pop(0)
                    del tlb[ancienne_page]
                tlb[page] = cadre
                ordre.append(page)

        physique = None
        if cadre is not None:
            physique = cadre * taille_page + deplacement
        lignes.append((adresse, page, deplacement, cadre, physique, hit))

    return lignes, hits


class OrdonnancementProprietesTests(unittest.TestCase):
    def assert_conforme_oracle(self, processus, algorithme, quantum=2):
        attendu_gantt, attendu_lignes = oracle_ordonnancement(
            processus, algorithme, quantum
        )
        gantt, lignes = ordonnancer(processus, algorithme, quantum)
        self.assertEqual(gantt, attendu_gantt)
        self.assertEqual(lignes, attendu_lignes)
        self.assert_mesures_coherentes(processus, gantt, lignes)

    def assert_mesures_coherentes(self, processus, gantt, lignes):
        par_nom = {}
        reste = {}
        for processus_un in processus:
            par_nom[processus_un["nom"]] = processus_un
            reste[processus_un["nom"]] = processus_un["duree"]

        horloge = 0
        fins = {}
        for nom, debut, fin in gantt:
            self.assertEqual(debut, horloge)
            self.assertGreater(fin, debut)
            if nom == "IDLE":
                for processus_un in processus:
                    disponible = processus_un["arrivee"] <= debut
                    self.assertFalse(
                        disponible and reste[processus_un["nom"]] > 0
                    )
            else:
                self.assertIn(nom, par_nom)
                self.assertLessEqual(par_nom[nom]["arrivee"], debut)
                consomme = fin - debut
                self.assertLessEqual(consomme, reste[nom])
                reste[nom] -= consomme
                fins[nom] = fin
            horloge = fin

        for nom in reste:
            self.assertEqual(reste[nom], 0)

        self.assertEqual(len(lignes), len(processus))
        for ligne in lignes:
            nom, arrivee, duree, priorite, fin, attente, sejour = ligne
            self.assertEqual(fin, fins[nom])
            self.assertEqual(sejour, fin - arrivee)
            self.assertEqual(attente, sejour - duree)
            self.assertGreaterEqual(attente, 0)
            self.assertGreaterEqual(sejour, duree)

    def test_oracle_tick_par_tick_idle_egalites_et_frontiere_rr(self):
        scenarios = [
            [
                {"nom": "B", "arrivee": 2, "duree": 1, "priorite": 1},
                {"nom": "A", "arrivee": 2, "duree": 2, "priorite": 1},
                {"nom": "C", "arrivee": 8, "duree": 1, "priorite": 0},
            ],
            [
                {"nom": "P1", "arrivee": 0, "duree": 3, "priorite": 1},
                {"nom": "P2", "arrivee": 1, "duree": 2, "priorite": 0},
                {"nom": "P3", "arrivee": 2, "duree": 1, "priorite": 0},
            ],
        ]
        for numero, processus in enumerate(scenarios):
            for algorithme in ("fcfs", "sjf", "priorite"):
                with self.subTest(scenario=numero, algorithme=algorithme):
                    self.assert_conforme_oracle(processus, algorithme)
            for quantum in (1, 2):
                with self.subTest(scenario=numero, algorithme="rr", quantum=quantum):
                    self.assert_conforme_oracle(processus, "rr", quantum)

        gantt, _ = ordonnancer(scenarios[1], "rr", 2)
        self.assertEqual(
            gantt,
            [("P1", 0, 2), ("P2", 2, 4),
             ("P3", 4, 5), ("P1", 5, 6)],
        )

    def test_oracle_exhaustif_deux_petits_processus(self):
        variantes = list(itertools.product((0, 2), (1, 2), (0, 1)))
        for donnees_a in variantes:
            for donnees_b in variantes:
                processus = [
                    {
                        "nom": "B",
                        "arrivee": donnees_b[0],
                        "duree": donnees_b[1],
                        "priorite": donnees_b[2],
                    },
                    {
                        "nom": "A",
                        "arrivee": donnees_a[0],
                        "duree": donnees_a[1],
                        "priorite": donnees_a[2],
                    },
                ]
                for algorithme in ("fcfs", "sjf", "priorite"):
                    with self.subTest(
                        a=donnees_a, b=donnees_b, algorithme=algorithme
                    ):
                        self.assert_conforme_oracle(processus, algorithme)
                for quantum in (1, 2):
                    with self.subTest(a=donnees_a, b=donnees_b, quantum=quantum):
                        self.assert_conforme_oracle(processus, "rr", quantum)

    def test_aliases_et_validation_stricte(self):
        processus = [
            {"nom": "A", "arrivee": 0, "duree": 2, "priorite": 0},
            {"nom": "B", "arrivee": 1, "duree": 1, "priorite": 1},
        ]
        self.assertEqual(
            ordonnancer(processus, "priority"),
            ordonnancer(processus, "priorite"),
        )
        self.assertEqual(
            ordonnancer(processus, "round_robin", 1),
            ordonnancer(processus, "rr", 1),
        )

        invalides = [
            ((), "fcfs", 2),
            ([{"nom": "A", "arrivee": True, "duree": 1, "priorite": 0}], "fcfs", 2),
            ([{"nom": "A", "arrivee": 0, "duree": True, "priorite": 0}], "fcfs", 2),
            ([{"nom": "A", "arrivee": 0, "duree": 1, "priorite": False}], "fcfs", 2),
            ([{"nom": "A", "arrivee": 0, "duree": 1, "priorite": 0,
               "extra": 1}], "fcfs", 2),
            ([{"nom": "A", "arrivee": 0, "duree": 1, "priorite": 0},
              {"nom": "A", "arrivee": 1, "duree": 1, "priorite": 0}], "fcfs", 2),
            (processus, None, 2),
            (processus, "rr", True),
        ]
        for entree, algorithme, quantum in invalides:
            with self.subTest(entree=entree, algorithme=algorithme):
                with self.assertRaises(ValueError):
                    ordonnancer(entree, algorithme, quantum)


class RemplacementProprietesTests(unittest.TestCase):
    def test_oracle_exhaustif_et_borne_optimal(self):
        for nombre_cadres in (1, 2, 3):
            for longueur in range(5):
                for references in itertools.product((0, 1, 2), repeat=longueur):
                    resultats = {}
                    for algorithme in ("fifo", "lru", "optimal"):
                        with self.subTest(
                            cadres=nombre_cadres,
                            references=references,
                            algorithme=algorithme,
                        ):
                            attendu = oracle_remplacement(
                                list(references), nombre_cadres, algorithme
                            )
                            obtenu = remplacer(
                                list(references), nombre_cadres, algorithme
                            )
                            self.assertEqual(obtenu, attendu)
                            resultats[algorithme] = obtenu[0]
                    self.assertLessEqual(resultats["optimal"], resultats["fifo"])
                    self.assertLessEqual(resultats["optimal"], resultats["lru"])

    def test_hits_connus_et_symetrie_renommage_pages(self):
        references = [1, 2, 1, 3, 1]
        hits_attendus = {
            "fifo": [False, False, True, False, False],
            "lru": [False, False, True, False, True],
            "optimal": [False, False, True, False, True],
        }
        for algorithme in hits_attendus:
            with self.subTest(algorithme=algorithme):
                defauts, trace = remplacer(references, 2, algorithme)
                self.assertEqual([ligne[1] for ligne in trace], hits_attendus[algorithme])
                self.assertEqual(defauts, 5 - sum(hits_attendus[algorithme]))

        references = [0, 2, 1, 0, 3, 2, 4, 0, 1]
        renommage = {0: 12, 1: 7, 2: 19, 3: 4, 4: 25}
        renommees = []
        for page in references:
            renommees.append(renommage[page])
        for algorithme in ("fifo", "lru", "optimal"):
            with self.subTest(symetrie=algorithme):
                original = remplacer(references, 3, algorithme)
                renomme = remplacer(renommees, 3, algorithme)
                trace_renommee = []
                for page, hit, victime, cadres in original[1]:
                    cadres_renommes = []
                    for cadre in cadres:
                        if cadre is None:
                            cadres_renommes.append(None)
                        else:
                            cadres_renommes.append(renommage[cadre])
                    if victime is None:
                        victime_renommee = None
                    else:
                        victime_renommee = renommage[victime]
                    trace_renommee.append(
                        (renommage[page], hit, victime_renommee, cadres_renommes)
                    )
                self.assertEqual(renomme, (original[0], trace_renommee))

    def test_validation_entiers_et_types_memoire(self):
        invalides = [
            ("012", 1, "fifo"),
            ([True], 1, "fifo"),
            ([0], True, "fifo"),
            ([0], 1, True),
            ([0], 0, "fifo"),
            ([0], 1, "autre"),
        ]
        for pages, cadres, algorithme in invalides:
            with self.subTest(pages=pages, cadres=cadres, algorithme=algorithme):
                with self.assertRaises(ValueError):
                    remplacer(pages, cadres, algorithme)


class TraductionProprietesTests(unittest.TestCase):
    def test_oracle_lru_capacite_zero_absence_et_cadre_zero(self):
        cas = [
            ([0, 4, 0, 8, 4], 4, {0: 0, 1: 1, 2: 2}, 2),
            ([0, 0, 4], 4, {0: 0, 1: 3}, 0),
            ([5, 70, 75, 130, 5, 195, 70, 260], 64,
             {0: 5, 1: 2, 2: 7, 3: 1}, 2),
            ([0, 12, 0, 12], 4, {0: 0}, 1),
        ]
        for adresses, taille, table, capacite in cas:
            with self.subTest(adresses=adresses, capacite=capacite):
                attendu = oracle_traduction(adresses, taille, table, capacite)
                obtenu = traduire(adresses, taille, table, capacite)
                self.assertEqual(obtenu, attendu)

        lignes, hits = traduire([0, 4, 0, 8, 4], 4, {0: 0, 1: 1, 2: 2}, 2)
        self.assertEqual([ligne[-1] for ligne in lignes], [False, False, True, False, False])
        self.assertEqual(hits, 1)
        self.assertEqual(lignes[0], (0, 0, 0, 0, 0, False))

    def test_validation_tlb_et_calculs_eat(self):
        invalides = [
            ([True], 4, {0: 0}, 1),
            ([0], True, {0: 0}, 1),
            ([0], 4, {True: 0}, 1),
            ([0], 4, {0: True}, 1),
            ([0], 4, {0: 0}, True),
            ([0], 4, [], 1),
        ]
        for adresses, taille, table, capacite in invalides:
            with self.subTest(table=table, capacite=capacite):
                with self.assertRaises(ValueError):
                    traduire(adresses, taille, table, capacite)

        self.assertEqual(calculer_eat(1, 8), 197.5)
        self.assertEqual(calculer_eat_defauts(0.1, 100, 1000), 190.0)
        for appel in (
            (calculer_eat, (True, 1)),
            (calculer_eat, (0, 1, math.inf, 100)),
            (calculer_eat_defauts, (True,)),
            (calculer_eat_defauts, (0.5, -1)),
        ):
            fonction, arguments = appel
            with self.subTest(fonction=fonction.__name__, arguments=arguments):
                with self.assertRaises(ValueError):
                    fonction(*arguments)


if __name__ == "__main__":
    unittest.main()
