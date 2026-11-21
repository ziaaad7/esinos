"""Présentation déterministe des résultats du simulateur."""
from .scheduler import ordonnancer
from .memory import remplacer, traduire, calculer_eat, calculer_eat_defauts
from .filesystem import lister_inodes, etat_disque
from .affichage import gantt_texte, tableau_texte


def titre(texte):
    print("\n" + texte)
    print("-" * len(texte))


def afficher_cpu(processus, algorithme, quantum=2):
    gantt, lignes = ordonnancer(processus, algorithme, quantum)
    titre(algorithme.upper())
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


def afficher_remplacement(pages, cadres, algorithme):
    defauts, trace = remplacer(pages, cadres, algorithme)
    titre(f"{algorithme.upper()} - {cadres} CADRES")
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
                        temps_tlb=10, temps_memoire=100):
    lignes, hits = traduire(adresses, taille, table, capacite)
    eat = calculer_eat(hits, len(lignes), temps_tlb, temps_memoire)
    titre("TRADUCTION, TLB ET EAT")
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
