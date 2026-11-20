"""Explications pas à pas construites à partir des traces ESINOS."""


def texte_cadres(cadres):
    """Affiche les cadres, avec « libre » pour un cadre vide."""
    texte = "["
    for index in range(len(cadres)):
        if index > 0:
            texte = texte + ", "
        if cadres[index] is None:
            texte = texte + "libre"
        else:
            texte = texte + str(cadres[index])
    return texte + "]"


def texte_cache(cache):
    """Affiche le TLB du moins récent au plus récent."""
    if len(cache) == 0:
        return "vide"
    texte = "["
    for index in range(len(cache)):
        if index > 0:
            texte = texte + ", "
        page, cadre = cache[index]
        texte = texte + f"p{page}→c{cadre}"
    return texte + "]"


def position_page(cadres, page):
    """Renvoie le numéro du cadre contenant page, ou None."""
    for numero in range(len(cadres)):
        if cadres[numero] == page:
            return numero
    return None


def prochaine_reference(page, pages, indice):
    """Renvoie le numéro humain de la prochaine référence, ou None."""
    for futur in range(indice + 1, len(pages)):
        if pages[futur] == page:
            return futur + 1
    return None


def texte_numeros(numeros):
    """Écrit une courte liste de numéros avec des boucles simples."""
    texte = ""
    for index in range(len(numeros)):
        if index > 0:
            texte = texte + ", "
        texte = texte + str(numeros[index])
    return texte


def raison_optimal(cadres, pages, indice, victime):
    """Explique le choix Optimal à partir du futur connu."""
    cadre_victime = position_page(cadres, victime)
    suivante = prochaine_reference(victime, pages, indice)
    memes = []
    for numero in range(len(cadres)):
        if prochaine_reference(cadres[numero], pages, indice) == suivante:
            memes.append(numero)

    if suivante is None and len(memes) > 1:
        return (
            f"Optimal constate que les pages des cadres {texte_numeros(memes)} "
            "ne sont jamais reprises. Égalité : il choisit le plus petit "
            f"numéro de cadre, donc le cadre {cadre_victime}."
        )
    if suivante is None:
        return (f"Optimal choisit la page {victime} du cadre {cadre_victime} "
                "car elle n'est jamais reprise.")
    if len(memes) > 1:
        return (
            f"Optimal voit que les pages des cadres {texte_numeros(memes)} "
            f"reviennent à la même référence {suivante}. Égalité : il choisit "
            f"le plus petit numéro de cadre, donc le cadre {cadre_victime}."
        )
    return (f"Optimal choisit la page {victime} du cadre {cadre_victime} car "
            f"sa prochaine utilisation est la plus lointaine, à la référence "
            f"{suivante}.")


def explications_remplacement(pages, nombre_cadres, algorithme, trace):
    """Explique une trace de remplacer, une phrase par référence."""
    if len(pages) != len(trace):
        raise ValueError("La trace doit avoir une étape par référence.")
    if nombre_cadres < 1:
        raise ValueError("Il faut au moins un cadre.")
    algorithme = algorithme.lower().strip()
    if algorithme not in ("fifo", "lru", "optimal"):
        raise ValueError("Algorithme attendu : fifo, lru ou optimal.")

    cadres_avant = [None] * nombre_cadres
    chargee_a = {}
    utilisee_a = {}
    explications = []
    for indice in range(len(pages)):
        page = pages[indice]
        page_trace, hit, victime, cadres_apres = trace[indice]
        numero = indice + 1
        if page_trace != page or len(cadres_apres) != nombre_cadres:
            raise ValueError("La trace ne correspond pas aux références.")

        texte = (f"Référence {numero}, page {page}. Avant : "
                 f"{texte_cadres(cadres_avant)}. ")
        if hit and algorithme == "fifo":
            texte = texte + ("Hit : la page est déjà en mémoire. FIFO ne "
                             "change pas l'ordre de chargement.")
        elif hit and algorithme == "lru":
            texte = texte + (f"Hit : la page est déjà en mémoire. LRU "
                             f"rafraîchit la page {page} : elle devient la "
                             "plus récemment utilisée.")
        elif hit:
            texte = texte + ("Hit : la page est déjà en mémoire, donc "
                             "Optimal ne remplace aucun cadre.")
        elif victime is None:
            libre = position_page(cadres_avant, None)
            texte = texte + (f"Défaut de page. Le cadre {libre} est libre, "
                             "la page y est chargée.")
        elif algorithme == "fifo":
            cadre = position_page(cadres_avant, victime)
            texte = texte + (f"Défaut de page, mémoire pleine. FIFO choisit "
                             f"la page {victime} du cadre {cadre}, chargée à "
                             f"la référence {chargee_a[victime]}, la plus ancienne.")
        elif algorithme == "lru":
            cadre = position_page(cadres_avant, victime)
            texte = texte + (f"Défaut de page, mémoire pleine. LRU choisit "
                             f"la page {victime} du cadre {cadre}, utilisée "
                             f"pour la dernière fois à la référence "
                             f"{utilisee_a[victime]}.")
        else:
            texte = texte + ("Défaut de page, mémoire pleine. "
                             + raison_optimal(cadres_avant, pages, indice, victime))

        if not hit:
            if victime is not None:
                del chargee_a[victime]
                del utilisee_a[victime]
            chargee_a[page] = numero
        utilisee_a[page] = numero
        explications.append(f"{texte} Après : {texte_cadres(cadres_apres)}.")
        cadres_avant = cadres_apres.copy()
    return explications


def index_cache(cache, page):
    """Renvoie la position d'une page dans le TLB, ou -1."""
    for index in range(len(cache)):
        if cache[index][0] == page:
            return index
    return -1


def explications_traduction(adresses, taille_page, table, capacite, lignes):
    """Explique une trace de traduire, une phrase par adresse."""
    if len(adresses) != len(lignes):
        raise ValueError("Il faut une ligne de trace par adresse.")
    if taille_page < 1 or capacite < 0:
        raise ValueError("Taille de page ou capacité TLB invalide.")

    cache = []
    explications = []
    for indice in range(len(adresses)):
        adresse = adresses[indice]
        adresse_trace, page, deplacement, cadre, physique, hit = lignes[indice]
        page_calculee = adresse // taille_page
        deplacement_calcule = adresse % taille_page
        if (adresse_trace != adresse or page != page_calculee
                or deplacement != deplacement_calcule):
            raise ValueError("Une ligne ne correspond pas à son adresse.")

        texte = (f"Adresse {adresse}, accès {indice + 1}. Page = {adresse} // "
                 f"{taille_page} = {page}, déplacement = {adresse} % "
                 f"{taille_page} = {deplacement}. TLB avant : "
                 f"{texte_cache(cache)}. ")
        if page not in table or cadre is None:
            texte = texte + (f"Miss TLB et défaut de page : la page {page} "
                             "est absente de la table. cadre=None et adresse "
                             "physique=None.")
        elif hit:
            position = index_cache(cache, page)
            if position == -1:
                raise ValueError("Un hit TLB est absent de l'état précédent.")
            cache.pop(position)
            cache.append((page, cadre))
            texte = texte + (f"Hit TLB : la page {page} est dans le cadre "
                             f"{cadre}. LRU la rafraîchit comme entrée la plus récente.")
        elif capacite == 0:
            texte = texte + ("Miss TLB : la capacité est 0, le cache est "
                             f"désactivé. La table donne le cadre {cadre}.")
        else:
            texte = texte + f"Miss TLB : la table des pages donne le cadre {cadre}."
            if len(cache) >= capacite:
                page_sortie, cadre_sorti = cache.pop(0)
                texte = texte + (f" LRU évince la page {page_sortie} du "
                                 f"cadre {cadre_sorti}.")
            cache.append((page, cadre))

        if cadre == 0:
            texte = texte + " Le cadre 0 est valide : il n'indique pas une absence."
        if physique is not None:
            texte = texte + (f" Adresse physique = {cadre} × {taille_page} + "
                             f"{deplacement} = {physique}.")
        explications.append(f"{texte} TLB après : {texte_cache(cache)}.")
    return explications
