"""Présentation des résultats : aucune saisie clavier sauf le pas à pas."""
from .scheduler import ordonnancer
from .memory import remplacer, traduire, calculer_eat, calculer_eat_defauts
from .filesystem import lister_inodes, etat_disque
from .affichage import gantt_texte, tableau_texte, explication_cpu
from .pedagogie import explications_remplacement, explications_traduction


def titre(texte):
    print("\n" + texte)
    print("-" * len(texte))


def parcourir_etapes(explications, mode):
    for explication in explications:
        print("\n" + explication)
        if mode == "pasapas":
            suite = input("Entrée : suite | t : tout afficher | 0 : retour : ")
            if suite.strip().lower() == "t":
                mode = "explique"
            elif suite.strip() == "0":
                return False
    return True


def afficher_cpu(processus, algorithme, quantum=2, mode="resume"):
    gantt, lignes = ordonnancer(processus, algorithme, quantum)
    titre(algorithme.upper())
    if mode != "resume":
        textes = explication_cpu(processus, gantt, algorithme, quantum)
        if not parcourir_etapes(textes, mode):
            return
    print(gantt_texte(gantt))
    print(tableau_texte(
        ("PID", "AT", "BT", "Prio", "Fin (CT)", "Attente", "Séjour"), lignes
    ))
    attente_totale = 0
    sejour_total = 0
    for ligne in lignes:
        attente_totale += ligne[5]
        sejour_total += ligne[6]
    print(f"Attente moyenne : {attente_totale / len(lignes):.2f}")
    print(f"Séjour moyen : {sejour_total / len(lignes):.2f}")


def comparer_cpu(processus, quantum=2):
    titre("COMPARAISON CPU - MÊMES PROCESSUS")
    resultats = []
    for algorithme in ("fcfs", "sjf", "rr", "priorite"):
        gantt, lignes = ordonnancer(processus, algorithme, quantum)
        print("\n" + algorithme.upper())
        print(gantt_texte(gantt))
        print(tableau_texte(
            ("PID", "AT", "BT", "Prio", "Fin (CT)", "Attente", "Séjour"), lignes
        ))
        attente = 0
        sejour = 0
        for ligne in lignes:
            attente += ligne[5]
            sejour += ligne[6]
        resultats.append((algorithme.upper(), f"{attente / len(lignes):.2f}",
                          f"{sejour / len(lignes):.2f}"))
    print(tableau_texte(("Algorithme", "Attente moyenne", "Séjour moyen"), resultats))
    print(f"Round Robin utilise un quantum de {quantum}.")


def afficher_remplacement(pages, cadres, algorithme, mode="resume"):
    defauts, trace = remplacer(pages, cadres, algorithme)
    titre(f"{algorithme.upper()} - {cadres} CADRES")
    if mode != "resume":
        textes = explications_remplacement(pages, cadres, algorithme, trace)
        if not parcourir_etapes(textes, mode):
            return
    lignes = []
    etape = 1
    for page, hit, victime, etat_cadres in trace:
        resultat = "défaut"
        if hit:
            resultat = "hit"
        lignes.append((etape, page, resultat, victime, str(etat_cadres)))
        etape += 1
    print(tableau_texte(("Étape", "Page", "Résultat", "Victime", "Cadres"), lignes))
    print(f"{algorithme.upper()} : {defauts} défauts")


def comparer_remplacement(pages, cadres):
    resultats = []
    for algorithme in ("fifo", "lru", "optimal"):
        defauts, trace = remplacer(pages, cadres, algorithme)
        taux = 0
        if pages:
            taux = 100 * defauts / len(pages)
        resultats.append((algorithme.upper(), defauts, len(pages) - defauts,
                          f"{taux:.2f} %"))
    titre(f"COMPARAISON MÉMOIRE - {cadres} CADRES")
    print(tableau_texte(("Algorithme", "Défauts", "Hits", "Taux de défaut"), resultats))


def afficher_traduction(adresses, taille, table, capacite,
                        temps_tlb=10, temps_memoire=100, mode="resume"):
    lignes, hits = traduire(adresses, taille, table, capacite)
    eat = calculer_eat(hits, len(lignes), temps_tlb, temps_memoire)
    titre("TRADUCTION, TLB ET EAT")
    if mode != "resume":
        textes = explications_traduction(adresses, taille, table, capacite, lignes)
        if not parcourir_etapes(textes, mode):
            return
    tableau = []
    for adresse, page, deplacement, cadre, physique, hit in lignes:
        resultat = "miss"
        if hit:
            resultat = "hit"
        if physique is None:
            resultat = "miss et défaut de page"
        tableau.append((adresse, page, deplacement, cadre, physique, resultat))
    print(tableau_texte(("Adresse", "Page", "Déplacement", "Cadre", "Physique", "TLB"),
                        tableau))
    print(f"Hits TLB : {hits}/{len(lignes)}")
    if mode != "resume":
        taux = hits / len(lignes)
        print(f"Chemin hit : {temps_tlb:g} + {temps_memoire:g} = "
              f"{temps_tlb + temps_memoire:g} ns")
        print(f"Chemin miss : {temps_tlb:g} + 2 x {temps_memoire:g} = "
              f"{temps_tlb + 2 * temps_memoire:g} ns")
        print(f"EAT = {taux:.3f} x coût hit + {1 - taux:.3f} x coût miss")
        print("Le délai de chargement d'une page depuis le disque est exclu.")
    print(f"EAT : {eat:.2f} ns")


def afficher_inodes(chemin):
    lignes = []
    inodes = lister_inodes(chemin)
    for index in range(len(inodes)):
        inode = inodes[index]
        if inode is None:
            lignes.append((index + 1, "libre", None, None, None))
        else:
            lignes.append((inode["numero"], "occupé", inode["nom"],
                           inode["taille"], str(inode["blocs"])))
    print(tableau_texte(("Inode", "État", "Nom", "Octets", "Blocs"), lignes))


def afficher_fichiers(chemin):
    lignes = []
    for inode in lister_inodes(chemin):
        if inode is not None:
            lignes.append((inode["numero"], inode["nom"], inode["taille"],
                           str(inode["blocs"])))
    print(tableau_texte(("Inode", "Nom", "Octets", "Blocs"), lignes))


def afficher_etat(chemin):
    etat = etat_disque(chemin)
    print("Format :", etat["format"])
    print(f"Blocs de données utilisés : {etat['blocs_utilises']}/{etat['nombre_blocs']}")
    print(f"Inodes utilisés : {etat['inodes_utilises']}/{etat['nombre_inodes']}")
    print(f"Taille d'un bloc : {etat['taille_bloc']} octets")


def afficher_eat_defauts(taux, temps_memoire=100, temps_defaut=1000000):
    resultat = calculer_eat_defauts(taux, temps_memoire, temps_defaut)
    titre("EAT AVEC DÉFAUTS DE PAGE")
    print("temps_defaut comprend tout le traitement du défaut, en ns.")
    print("EAT = (1 - p) × temps_mémoire + p × temps_défaut")
    print(f"p = {taux:g} ; mémoire = {temps_memoire:g} ns ; "
          f"défaut = {temps_defaut:g} ns")
    print(f"EAT avec défauts : {resultat:.2f} ns")
