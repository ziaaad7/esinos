"""Explications pas à pas construites à partir des traces ESINOS."""


def texte_cadres(cadres):
    """Affiche les cadres, avec « libre » pour un cadre vide."""
    elements = []
    for cadre in cadres:
        elements.append("libre" if cadre is None else str(cadre))
    return "[" + ", ".join(elements) + "]"


def texte_cache(cache):
    """Affiche le TLB du moins récent au plus récent."""
    if not cache:
        return "vide"
    elements = []
    for page, cadre in cache:
        elements.append(f"p{page}→c{cadre}")
    return "[" + ", ".join(elements) + "]"


def _raison_optimal(cadres, pages, indice, victime):
    suivantes = []
    for page in cadres:
        try:
            suivantes.append(pages.index(page, indice + 1) + 1)
        except ValueError:
            suivantes.append(None)
    cadre = cadres.index(victime)
    suivante = suivantes[cadre]
    egaux = []
    for numero in range(len(cadres)):
        if suivantes[numero] == suivante:
            egaux.append(str(numero))
    if len(egaux) > 1:
        cadres_egaux = ", ".join(egaux)
        if suivante is None:
            raison = (
                f"Optimal constate que les pages des cadres {cadres_egaux} "
                "ne sont jamais reprises"
            )
        else:
            raison = (
                f"Optimal voit que les pages des cadres {cadres_egaux} "
                f"reviennent à la même référence {suivante}"
            )
        return (
            f"{raison}. Égalité : il choisit le plus petit numéro de cadre, "
            f"donc le cadre {cadre}."
        )
    if suivante is None:
        return (f"Optimal choisit la page {victime} du cadre {cadre} car elle "
                "n'est jamais reprise.")
    return (f"Optimal choisit la page {victime} du cadre {cadre} car sa "
            f"prochaine utilisation est la plus lointaine, à la référence "
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
    textes = []
    for indice, page in enumerate(pages):
        page_trace, hit, victime, cadres_apres = trace[indice]
        numero = indice + 1
        if page_trace != page or len(cadres_apres) != nombre_cadres:
            raise ValueError("La trace ne correspond pas aux références.")

        texte = f"Référence {numero}, page {page}. Avant : {texte_cadres(cadres_avant)}. "
        if hit:
            if algorithme == "fifo":
                texte += (
                    "Hit : la page est déjà en mémoire. FIFO ne change pas "
                    "l'ordre de chargement."
                )
            elif algorithme == "lru":
                texte += (
                    f"Hit : la page est déjà en mémoire. LRU rafraîchit la "
                    f"page {page} : elle devient la plus récemment utilisée."
                )
            else:
                texte += (
                    "Hit : la page est déjà en mémoire, donc Optimal ne "
                    "remplace aucun cadre."
                )
        elif victime is None:
            texte += (
                f"Défaut de page. Le cadre {cadres_avant.index(None)} est "
                "libre, la page y est chargée."
            )
        elif algorithme == "fifo":
            cadre = cadres_avant.index(victime)
            texte += (
                f"Défaut de page, mémoire pleine. FIFO choisit la page "
                f"{victime} du cadre {cadre}, chargée à la référence "
                f"{chargee_a[victime]}, la plus ancienne."
            )
        elif algorithme == "lru":
            cadre = cadres_avant.index(victime)
            texte += (
                f"Défaut de page, mémoire pleine. LRU choisit la page "
                f"{victime} du cadre {cadre}, utilisée pour la dernière fois "
                f"à la référence {utilisee_a[victime]}."
            )
        else:
            texte += "Défaut de page, mémoire pleine. " + _raison_optimal(
                cadres_avant, pages, indice, victime
            )

        if not hit:
            if victime is not None:
                del chargee_a[victime]
                del utilisee_a[victime]
            chargee_a[page] = numero
        utilisee_a[page] = numero
        textes.append(f"{texte} Après : {texte_cadres(cadres_apres)}.")
        cadres_avant = cadres_apres.copy()
    return textes
def explications_traduction(adresses, taille_page, table, capacite, lignes):
    """Explique une trace de traduire, une phrase par adresse."""
    if len(adresses) != len(lignes):
        raise ValueError("Il faut une ligne de trace par adresse.")
    if taille_page < 1 or capacite < 0:
        raise ValueError("Taille de page ou capacité TLB invalide.")

    cache = []
    textes = []
    for indice, adresse in enumerate(adresses):
        adresse_trace, page, deplacement, cadre, physique, hit = lignes[indice]
        page_calculee = adresse // taille_page
        deplacement_calcule = adresse % taille_page
        if (
            adresse_trace != adresse
            or page != page_calculee
            or deplacement != deplacement_calcule
        ):
            raise ValueError("Une ligne ne correspond pas à son adresse.")

        texte = (
            f"Adresse {adresse}, accès {indice + 1}. Page = {adresse} // "
            f"{taille_page} = {page}, déplacement = {adresse} % "
            f"{taille_page} = {deplacement}. TLB avant : {texte_cache(cache)}. "
        )
        if page not in table or cadre is None:
            texte += (
                f"Miss TLB et défaut de page : la page {page} est absente "
                "de la table. cadre=None et adresse physique=None."
            )
        elif hit:
            position = 0
            while position < len(cache) and cache[position][0] != page:
                position += 1
            if position == len(cache):
                raise ValueError("Un hit TLB est absent de l'état précédent.")
            cache.pop(position)
            cache.append((page, cadre))
            texte += (
                f"Hit TLB : la page {page} est dans le cadre {cadre}. "
                "LRU la rafraîchit comme entrée la plus récente."
            )
        elif capacite == 0:
            texte += (
                "Miss TLB : la capacité est 0, le cache est désactivé. "
                f"La table donne le cadre {cadre}."
            )
        else:
            texte += f"Miss TLB : la table des pages donne le cadre {cadre}."
            if len(cache) >= capacite:
                page_sortie, cadre_sorti = cache.pop(0)
                texte += f" LRU évince la page {page_sortie} du cadre {cadre_sorti}."
            cache.append((page, cadre))

        if cadre == 0:
            texte += " Le cadre 0 est valide : il n'indique pas une absence."
        if physique is not None:
            texte += (
                f" Adresse physique = {cadre} × {taille_page} + "
                f"{deplacement} = {physique}."
            )
        textes.append(f"{texte} TLB après : {texte_cache(cache)}.")
    return textes
