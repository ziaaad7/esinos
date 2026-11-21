# Architecture et stratégie de tests

## Vue d’ensemble

ESINOS 3.0.0 sépare calcul, saisie, affichage et persistance. La séparation
évite qu’un menu recalcule un algorithme ou qu’un rendu modifie des données. Le
paquet comprend 17 modules Python par rôle.

| Module | Rôle principal |
| --- | --- |
| __init__.py | Version et petite surface d’import |
| __main__.py | Lancement par python3 -m esinos |
| cli.py | Routage du menu principal et des sous-commandes |
| exemples.py | Jeux de données reproductibles |
| entrees.py | Lecture et validation des entrées texte |
| sorties.py | Présentation terminal et navigation pas à pas |
| menus_cpu.py | Sous-menu CPU et assistant de saisie |
| menus_memoire.py | Sous-menus pages, traduction et EAT défauts |
| menus_fichiers.py | Sous-menu des opérations sur disque |
| demonstration.py | Scénario complet reproductible |
| scheduler.py | Calcul du CPU, Gantt et statistiques |
| memory.py | Remplacement, traduction, TLB et deux EAT |
| filesystem.py | API texte/inodes et règles de haut niveau du disque |
| disque_binaire.py | Codec de l’image binaire, géométrie et CRC32 |
| affichage.py | Gantt, tableaux et explications CPU |
| pedagogie.py | Explications issues des traces mémoire |
| carte_disque.py | Carte des blocs et suivi d’un fichier |

## Cœur de calcul et présentation

scheduler.py est le seul module qui produit le Gantt et les mesures CPU. Son
contrat est :

~~~text
ordonnancer(processus, algorithme, quantum=2)
    -> (gantt, lignes)
~~~

sorties.py peut demander ce résultat et l’afficher, mais il ne redéfinit pas les
règles FCFS, SJF, Priority ou Round Robin. affichage.py construit le texte du
Gantt et vérifie qu’une explication CPU correspond bien au Gantt fourni.

memory.py expose trois calculs indépendants :

~~~text
remplacer(pages, nombre_cadres, algorithme)
    -> (nombre_defauts, trace)

traduire(adresses, taille_page, table_pages, capacite_tlb=2)
    -> (lignes, hits)

calculer_eat(hits, acces, temps_tlb=10, temps_memoire=100)
calculer_eat_defauts(taux_defaut, temps_memoire=100, temps_defaut=1000000)
~~~

pedagogie.py ne choisit pas une nouvelle victime. Il utilise la trace fournie
pour expliquer la décision déjà prise. sorties.py relie ces fonctions de calcul
à l’écran, puis les menus gardent seulement l’état de navigation et les valeurs
courantes.

## Entrées, menus et démonstration

entrees.py transforme les chaînes en dictionnaires de processus, listes
d’entiers et tables page→cadre. Il centralise les valeurs par défaut et les
contrôles de base.

menus_cpu.py, menus_memoire.py et menus_fichiers.py gèrent les choix
interactifs. cli.py les appelle depuis le menu principal et convertit les
arguments du Terminal. demonstration.py réutilise les mêmes API pour éviter un
scénario spécial qui divergerait du menu.

Le parcours Pas à pas est une responsabilité de sorties.py. Il ne modifie pas
la trace. Entrée continue, t passe en affichage complet et 0 abandonne le
parcours courant.

## Image disque binaire

La géométrie annoncée par nombre_blocs compte les **blocs de données
seulement**. Les métadonnées sont réservées avant eux, dans cet ordre logique :

~~~text
superbloc
bitmap des blocs de données
zone des inodes
répertoire
blocs de données, au nombre demandé
~~~

Le superbloc décrit notamment la géométrie. Le bitmap traite uniquement les
blocs de données. Les fichiers restent des textes UTF-8 et les noms restent
ASCII sur 1 à 64 caractères. Le format ne change donc pas le contrat utilisateur
des fonctions créer, lire et supprimer.

Un CRC32 vérifie la cohérence d’une image lue. Il détecte des erreurs
accidentelles ou une corruption simple. Ce n’est ni un chiffrement ni une preuve
cryptographique d’intégrité.

Le chemin par défaut est data/esinos.disk.img. Une ancienne image JSON peut être
lue sans être remplacée. La migration est explicite :

~~~bash
python3 -m esinos fs --disk ancien.json migrate nouveau.img
~~~

Elle écrit exclusivement nouveau.img et conserve ancien.json. Le menu fichiers
propose la même opération par son choix 10. Le guide détaillé est
[03-fichiers.md](03-fichiers.md).

## Écritures et concurrence

Une écriture sûre construit d’abord le nouvel état dans un fichier temporaire
du même dossier, puis remplace la destination seulement quand l’écriture est
complète. Une initialisation concurrente ne doit pas écraser silencieusement
une image créée par un autre processus : un seul appel gagne, l’autre reçoit une
erreur exploitable.

La migration suit la même prudence. Elle lit et valide la source, prépare une
destination distincte et laisse la source intacte en cas d’erreur. Un en-tête,
une taille, une table ou un CRC32 incohérents doivent provoquer un refus de
lecture plutôt qu’une interprétation approximative.

## Oracles indépendants et tests de propriétés

Un test utile ne doit pas demander au même calcul de prouver son propre
résultat. Les oracles indépendants utilisent donc des attendus écrits à la main
ou des propriétés vérifiables séparément.

- CPU : les tranches sont contiguës, aucune ne commence avant l’arrivée du
  processus, la somme de ses tranches vaut BT et CT est sa dernière borne.
- Round Robin : chaque tranche dure au plus le quantum, y compris la dernière
  d’un processus, et les arrivées à une borne sont observables avant sa réinsertion.
- Pages : une trace a une étape par référence, les cadres gardent leur taille,
  et Optimal ne produit pas plus de défauts que FIFO ou LRU sur la même suite.
- TLB : le nombre de hits correspond aux lignes marquées hit, la capacité n’est
  jamais dépassée et la capacité 0 désactive le cache.
- EAT : p=0 donne le temps mémoire, p=1 donne le temps total du défaut et les
  taux ou temps non finis sont refusés.
- Disque : créer puis rouvrir puis lire restitue le même UTF-8, un nom ou bloc
  corrompu est refusé, une migration conserve les octets de la source et une
  initialisation concurrente n’écrase pas l’image gagnante.

Les tests de propriétés complètent les exemples attendus. Ils servent
d’oracles séparés des fonctions utilisées par l’interface.

## Lancer la validation

~~~bash
cd code
python3 -m unittest discover -s tests -v
~~~

La version 3.0.0 comporte **88 tests automatisés**, tous réussis lors de la
validation locale. Plusieurs tests parcourent aussi des jeux exhaustifs et
comparent leurs résultats à des oracles indépendants.

Le workflow `.github/workflows/tests.yml` rejoue la suite et la démonstration
sur Linux (Python 3.9 et 3.12), Windows et macOS (Python 3.12).
