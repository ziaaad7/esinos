"""Mémoire virtuelle ESINOS avec des listes et des dictionnaires simples."""

from math import isfinite


def verifier_entier(valeur, nom, minimum=0):
    """Vérifie un entier et sa borne minimale."""
    if type(valeur) is not int:
        raise ValueError(nom + " doit être un entier.")
    if valeur < minimum:
        raise ValueError(nom + " est trop petit.")


def verifier_temps(temps):
    """Vérifie un temps numérique, fini et positif ou nul."""
    if type(temps) is not int and type(temps) is not float:
        raise ValueError("Les temps doivent être des nombres.")
    try:
        fini = isfinite(temps)
    except OverflowError:
        fini = False
    if temps < 0 or not fini:
        raise ValueError("Les temps doivent être positifs ou nuls.")


def cadre_a_remplacer(cadres, pages, indice, algorithme, fifo, dernier_usage):
    """Choisit la position du cadre libre ou de la victime."""
    if None in cadres:
        return cadres.index(None)

    if algorithme == "fifo":
        return fifo.pop(0)

    choix = 0
    if algorithme == "lru":
        for numero in range(1, len(cadres)):
            page = cadres[numero]
            page_choisie = cadres[choix]
            if dernier_usage[page] < dernier_usage[page_choisie]:
                choix = numero
        return choix

    # Optimal regarde la première réutilisation future de chaque page.
    plus_loin = -1
    for numero in range(len(cadres)):
        page = cadres[numero]
        prochain_usage = len(pages)
        for futur in range(indice + 1, len(pages)):
            if pages[futur] == page:
                prochain_usage = futur
                break
        if prochain_usage > plus_loin:
            plus_loin = prochain_usage
            choix = numero
    return choix


def remplacer(pages, nombre_cadres, algorithme):
    """Renvoie les défauts et la trace FIFO, LRU ou Optimal."""
    if not isinstance(pages, (list, tuple)):
        raise ValueError("pages doit être une liste ou un tuple.")
    pages_valides = []
    for page in pages:
        verifier_entier(page, "Chaque page", 0)
        pages_valides.append(page)

    verifier_entier(nombre_cadres, "Le nombre de cadres", 1)
    if type(algorithme) is not str:
        raise ValueError("L'algorithme doit être du texte.")
    algorithme = algorithme.lower().strip()
    if algorithme not in ("fifo", "lru", "optimal"):
        raise ValueError("Algorithme attendu : fifo, lru ou optimal.")

    cadres = [None] * nombre_cadres

    fifo = []
    dernier_usage = {}
    trace = []
    nombre_defauts = 0

    for indice in range(len(pages_valides)):
        page = pages_valides[indice]
        hit = page in cadres
        victime = None

        if hit:
            dernier_usage[page] = indice
        else:
            nombre_defauts = nombre_defauts + 1
            numero = cadre_a_remplacer(
                cadres,
                pages_valides,
                indice,
                algorithme,
                fifo,
                dernier_usage,
            )
            victime = cadres[numero]
            if victime is not None:
                del dernier_usage[victime]
            cadres[numero] = page
            dernier_usage[page] = indice
            if algorithme == "fifo":
                fifo.append(numero)

        trace.append((page, hit, victime, cadres.copy()))

    return nombre_defauts, trace


def traduire(adresses, taille_page, table_pages, capacite_tlb=2):
    """Traduit une liste d'adresses et garde un TLB LRU simple."""
    if not isinstance(adresses, (list, tuple)):
        raise ValueError("adresses doit être une liste ou un tuple.")
    adresses_valides = []
    for adresse in adresses:
        verifier_entier(adresse, "Chaque adresse", 0)
        adresses_valides.append(adresse)

    verifier_entier(taille_page, "La taille de page", 1)
    verifier_entier(capacite_tlb, "La capacité du TLB", 0)
    if not isinstance(table_pages, dict):
        raise ValueError("table_pages doit être un dictionnaire.")

    table_validee = {}
    for page in table_pages:
        cadre = table_pages[page]
        verifier_entier(page, "Chaque page de la table", 0)
        verifier_entier(cadre, "Chaque cadre de la table", 0)
        table_validee[page] = cadre

    tlb = {}
    ordre_tlb = []
    lignes = []
    hits = 0

    for adresse in adresses_valides:
        page = adresse // taille_page
        deplacement = adresse % taille_page
        cadre = None
        adresse_physique = None
        hit = False

        if capacite_tlb > 0 and page in tlb:
            cadre = tlb[page]
            hit = True
            hits = hits + 1
            ordre_tlb.remove(page)
            ordre_tlb.append(page)
        elif page in table_validee:
            cadre = table_validee[page]
            if capacite_tlb > 0:
                if len(ordre_tlb) >= capacite_tlb:
                    page_ancienne = ordre_tlb.pop(0)
                    del tlb[page_ancienne]
                tlb[page] = cadre
                ordre_tlb.append(page)

        # Le cadre 0 est valide. Seul None signifie une page absente.
        if cadre is not None:
            adresse_physique = cadre * taille_page + deplacement
        lignes.append(
            (adresse, page, deplacement, cadre, adresse_physique, hit)
        )

    return lignes, hits


def calculer_eat(hits, acces, temps_tlb=10, temps_memoire=100):
    """Calcule l'EAT sans la pénalité de chargement d'une page."""
    verifier_entier(hits, "Le nombre de hits", 0)
    verifier_entier(acces, "Le nombre d'accès", 1)
    if hits > acces:
        raise ValueError("Les hits ne peuvent pas dépasser les accès.")

    for temps in (temps_tlb, temps_memoire):
        verifier_temps(temps)

    taux_hit = hits / acces
    # Forme regroupée de la moyenne des coûts hit et miss.
    resultat = temps_tlb + (2 - taux_hit) * temps_memoire

    if not isfinite(resultat):
        raise ValueError("Le résultat EAT doit être fini.")
    return resultat
