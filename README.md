# ESINOS - mini-noyau simule

ESINOS simule en espace utilisateur des mécanismes fondamentaux d'un système
d'exploitation. Il affiche les décisions de l'ordonnanceur et du gestionnaire
de mémoire. Le bonus utilise un fichier JSON comme disque virtuel.

Le projet couvre les deux volets obligatoires du sujet :

- un ordonnanceur de processus avec **FCFS**, **SJF**, **Round Robin** et
  **priorite**, un diagramme de Gantt et les temps moyens ;
- une simulation de pagination avec traduction logique-vers-physique,
  remplacement **FIFO**, **LRU** et **Optimal**, TLB et calcul de l'EAT.

Le bonus est un mini-systeme de fichiers a inodes persistant dans une image
disque JSON : creation, lecture, suppression et affichage de la table
d'inodes.

## Prerequis

- Python 3.9 ou plus recent ;
- `make` pour les raccourcis de test (facultatif).

Aucune dependance externe n'est requise : le projet s'appuie uniquement sur la
bibliotheque standard de Python.

## Installation et lancement

Le code est autonome. Depuis la racine du livrable :

```bash
cd code
python3 -m esinos
```

La commande ouvre le menu interactif. Les saisies sont validees : une valeur
invalide est expliquee sans interrompre la session.

Pour lancer une presentation reproductible des fonctions principales :

```bash
cd code
python3 -m esinos demo
```

La demonstration est volontairement deterministe ; elle constitue un bon fil
conducteur pour la video et la soutenance.

## Menu et demonstrations

Le menu integre les trois simulateurs.

| Volet | Ce que montre la demonstration |
| --- | --- |
| Ordonnancement | Le Gantt obtenu avec FCFS, SJF, Round Robin et priorite, puis les temps d'attente et de sejour moyens. |
| Memoire virtuelle | La traduction des references, les defauts de page, l'etat des cadres et les evictions FIFO, LRU ou Optimal. |
| TLB / EAT | L'adresse 75 réutilise la traduction de l'adresse 70. La démo affiche 1 hit sur 8 accès et un EAT de 197,50 ns. |
| Systeme de fichiers (bonus) | La creation, la lecture et la suppression d'un fichier, puis la table d'inodes et les blocs occupes. |

Exemple de session rapide :

```text
$ cd code
$ python3 -m esinos demo

=== ESINOS : demonstration integree ===
[Ordonnancement] ... Gantt et moyennes
[Memoire] ... traduction et evictions
[Fichiers] ... inode(s) et blocs
```

Le contenu exact affiche depend des jeux de references integres a la demo ; les
calculs, et non un resultat fige, sont produits par les modules du projet.

## Architecture

```text
code/
├── esinos/
│   ├── __init__.py       # paquet et API publique
│   ├── __main__.py       # point d'entree : python3 -m esinos
│   ├── cli.py            # menu, affichage et validation des saisies
│   ├── scheduler.py      # processus, algorithmes et statistiques
│   ├── memory.py         # pagination, TLB, EAT et remplacement
│   └── filesystem.py     # bonus : inodes, blocs et operations fichiers
├── tests/                # tests unitaires et cas limites
└── Makefile              # raccourcis d'execution et de test
```

Cette separation evite que la logique d'algorithme soit melangee a
l'interaction terminal. Les modules `scheduler`, `memory` et `filesystem`
peuvent donc etre testes directement et le menu se limite a presenter les
resultats.

### Ordonnancement

Chaque processus contient au minimum son identifiant, son instant d'arrivee,
sa duree CPU et, pour l'algorithme de priorite, son niveau de priorite. Le
simulateur conserve les segments d'execution afin de construire le Gantt et
calcule :

```text
temps de sejour = fin - arrivee
temps d'attente = temps de sejour - duree CPU
```

Les criteres de departage sont deterministes (arrivee puis identifiant) afin
que deux executions du meme scenario donnent le meme resultat.

### Memoire

Une adresse logique est découpée en numéro de page et déplacement. L'écran
de traduction utilise une table préchargée et signale les pages absentes.
Dans l'écran de remplacement, les algorithmes attribuent les cadres en
suivant une suite de références. Le TLB met en cache les traductions
récentes. Le modèle calcule l'EAT avec la formule suivante.

```text
EAT = h × (t_TLB + t_mem) + (1 - h) × (t_TLB + 2 × t_mem)
```

Dans cette formule, `h` désigne le taux de succès du TLB et `t_mem` le
temps d'un accès mémoire. Les durées doivent être finies et positives ou
nulles. Le modèle omet la pénalité de chargement d'une page absente.

### Systeme de fichiers (bonus)

Le mini-systeme de fichiers gere une table d'inodes et un espace de blocs
simule. Un inode porte les metadonnees et les blocs associes au fichier. Les
operations refusent les noms invalides, les fichiers inexistants et les
allocations qui depassent la capacite disponible, sans corrompre l'etat deja
enregistre.

Depuis `code/`, la commande suivante crée une image neuve. Utilisez un
nouveau nom si l'image existe déjà.

```bash
python3 -m esinos fs --disk data/exemple.disk.json --blocks 8 --block-size 16 init
```

`fs init` refuse un chemin déjà occupé. Le choix « Reformater » du menu
interactif demande confirmation avant d'effacer une image chargée.

## Tests

Depuis `code/` :

```bash
make test
```

La suite teste notamment :

- l'ordre et les statistiques des quatre ordonnanceurs ;
- les cas d'arrivee differes, de processeur inactif et de quantum Round Robin ;
- les traductions, defauts de page et evictions FIFO/LRU/Optimal ;
- les hits et misses TLB, la démo et le rejet de durées EAT non finies ;
- l'allocation, la lecture et la libération des blocs, ainsi que la protection
  des images disque existantes à l'initialisation.

Pour lancer les tests sans `make` :

```bash
python3 -m unittest discover -s tests -v
```

## Exemples de scenarios a presenter

1. Choisir trois ou quatre processus aux arrivees et durees distinctes,
   comparer FCFS, SJF et Round Robin, puis expliquer l'effet du quantum.
2. Donner une chaine de references de pages suffisamment longue pour provoquer
   plusieurs evictions ; montrer FIFO pas a pas, puis comparer son nombre de
   defauts a LRU.
3. Afficher les statistiques TLB et recalculer l'EAT a partir du taux de hit.
4. Creer un fichier du bonus, le lire, lister les inodes, puis le supprimer et
   verifier que ses blocs redeviennent libres.

## Limites assumees

ESINOS est un outil pedagogique, pas un vrai noyau. Il ne cree aucun processus
systeme et n'accede pas a la memoire physique. Les simulations d'ordonnancement
et de memoire vivent uniquement pendant l'execution ; le bonus de fichiers est
la seule exception, car son image-disque JSON est volontairement persistante.
Ces simplifications permettent de rendre les algorithmes, leurs etats
intermediaires et leurs compromis directement observables.

## Fichiers à remettre

- `code/` : code source commente ;
- `README.md` : ce guide d'execution ;
- `report.pdf` : rapport technique de 3 pages ;
- `demo.mp4` : vidéo de démonstration à enregistrer par le groupe, caméra
  ouverte. Placer le fichier à la racine, à côté de `report.pdf`.
