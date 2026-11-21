# ESINOS — Mini-noyau de système d’exploitation simulé

ESINOS est un simulateur pédagogique écrit en **Python**, qui rend observables
les mécanismes fondamentaux d’un système d’exploitation : l’ordonnancement du
processeur, la gestion de la mémoire et l’allocation de fichiers par inodes.

Il fonctionne en espace utilisateur : les processus, les cadres mémoire et le
disque sont des données simulées. Les résultats peuvent ainsi être vérifiés
sur de petits jeux de données reproductibles.

## Fonctionnalités

| Domaine du sujet | Fonctions réalisées | Accès dans le menu |
| --- | --- | --- |
| Ordonnancement CPU | FCFS, SJF, Round Robin et Priority ; Gantt ; temps d’attente et de séjour moyens | Choix 1 |
| Gestionnaire mémoire | Pagination, remplacement FIFO/LRU/Optimal, traduction logique vers physique, TLB et EAT | Choix 2 et 3 |
| Bonus prévu par le sujet | Création, lecture, suppression et allocation par inodes sur un fichier-disque persistant | Choix 4 |
| Démonstration | Scénario reproductible couvrant les fonctions principales | Choix 5 |

L’application utilise uniquement la bibliothèque standard de Python. Aucun
paquet externe ni service en ligne n’est nécessaire à son exécution.

## Prérequis et lancement

**Python 3.9 ou une version plus récente** est nécessaire. Git est utile pour
récupérer le dépôt ; `make` sert seulement à des raccourcis facultatifs.

### Première installation avec Git

Dans un terminal, exécuter :

```bash
git clone https://github.com/ziaaad7/esinos.git
cd esinos
cd code
python3 -m esinos
```

`cd esinos` entre dans le dépôt téléchargé, puis `cd code` entre dans le dossier
qui contient le paquet Python. La commande de lancement doit être exécutée
depuis ce dossier `code`.

### Projet déjà téléchargé

Ouvrir le dossier du projet, puis son sous-dossier `code`, dans le terminal.
Lancer ensuite :

```bash
python3 -m esinos
```

Sur le Mac où le projet est placé dans Documents :

```bash
cd ~/Documents/esinos/code
python3 -m esinos
```

Pour afficher l’aide ou la version :

```bash
python3 -m esinos --help
python3 -m esinos --version
```

## Utilisation du menu

| Choix | Écran | Utilisation |
| --- | --- | --- |
| 1 | Ordonnancement CPU | Choisir un algorithme, comparer les politiques ou saisir des processus |
| 2 | Gestionnaire mémoire | Simuler FIFO, LRU et Optimal sur une suite de références |
| 3 | Traduction, TLB et EAT | Traduire des adresses et mesurer les hits du TLB et le temps moyen d’accès |
| 4 | Système de fichiers à inodes | Créer, lire, supprimer et consulter la table d’inodes |
| 5 | Démonstration | Rejouer les exemples de référence sans saisie |
| 0 | Quitter | Fermer le simulateur |

Les choix **2 et 3 constituent les deux parcours de la gestion mémoire** : le
premier étudie le remplacement des pages, le second la traduction et son coût.

Une valeur entre crochets est la valeur proposée : appuyer sur Entrée permet
de la conserver. Les sous-menus gardent les données saisies pendant les essais.
Le choix `0` d’un sous-menu revient au menu principal.

### 1. Ordonnancement CPU

Un processus est défini par quatre données :

| Donnée | Signification |
| --- | --- |
| PID | Nom unique du processus |
| AT | Instant d’arrivée |
| BT | Durée d’exécution nécessaire sur le CPU |
| Priorité | Plus le nombre est petit, plus le processus est urgent |

Le sous-menu propose FCFS, SJF, Round Robin, Priority, une comparaison des quatre
politiques, une saisie guidée et le rétablissement de l’exemple. Round Robin
demande également un quantum strictement positif.

La simulation calcule la fin de chaque processus et les mesures suivantes :

```text
Temps de séjour (TAT) = fin (CT) - arrivée (AT)
Temps d’attente (WT)  = séjour (TAT) - durée CPU (BT)
```

Le résultat comprend un **diagramme de Gantt**, un tableau par processus et les
deux moyennes. Le Gantt est proportionnel lorsque les noms et les instants
tiennent dans le terminal. Pour les cas trop larges, un schéma conserve les
bornes exactes et indique explicitement qu’il n’est pas proportionnel.

**Conventions retenues :** FCFS, SJF et Priority sont non préemptifs. Les égalités
sont départagées par arrivée puis nom. Dans Round Robin, les nouvelles arrivées
entrent dans la file avant la réinsertion du processus interrompu. Une tranche
`IDLE` indique que le CPU est libre en attendant une arrivée. Le modèle utilise
un seul CPU, un burst par processus et aucun coût de changement de contexte.

### 2. Gestionnaire mémoire : remplacement de pages

L’utilisateur choisit une suite de références et un nombre de cadres. Lorsqu’une
page demandée est absente, le simulateur compte un défaut de page. Il utilise
un cadre libre ou sélectionne une victime lorsque tous les cadres sont occupés.

| Politique | Règle de remplacement |
| --- | --- |
| FIFO | Retirer la page chargée depuis le plus longtemps ; un hit ne change pas cet ordre |
| LRU | Retirer la page dont la dernière utilisation est la plus ancienne |
| Optimal | Retirer la page dont la prochaine utilisation est la plus lointaine, ou qui ne revient plus |

Le tableau affiche **chaque étape**, la page demandée, le hit ou défaut, la
victime éventuelle et les cadres après l’accès. Il permet de présenter l’éviction
FIFO étape par étape, puis de comparer avec LRU comme demandé dans le sujet.

La comparaison utilise les mêmes références et le même nombre de cadres pour
les trois politiques. Optimal connaît la suite future : il fournit une borne
théorique pour cette simulation.

### 3. Traduction d’adresses, TLB et EAT

Les paramètres sont la liste d’adresses logiques, la taille de page, la table
`page:cadre`, la capacité du TLB et les temps de consultation en nanosecondes.
La traduction applique :

```text
page         = adresse // taille_page
déplacement  = adresse % taille_page
adresse RAM  = cadre × taille_page + déplacement
```

Le cadre `0` est valide. Une page absente de la table ne donne pas d’adresse
physique et est signalée comme défaut de page.

Le **TLB** conserve les traductions récentes et utilise LRU pour choisir une
entrée à remplacer. Il commence vide à chaque nouvelle simulation et reste
actif pendant toute la suite d’adresses. Une capacité de `0` signifie qu’aucune
entrée n’est conservée.

L’**EAT** est la moyenne des coûts de consultation du TLB et de la mémoire :

```text
Coût d’un hit  = temps_TLB + temps_mémoire
Coût d’un miss = temps_TLB + 2 × temps_mémoire
EAT           = temps_TLB + (2 - taux_de_hit) × temps_mémoire
```

Ce modèle exclut le chargement d’une page depuis le disque. Dans la démonstration,
une page absente compte comme un miss pour cette moyenne ; le programme ne simule
pas le délai complet de traitement d’un défaut de page.

### 4. Bonus : système de fichiers à inodes

Le bonus utilise un fichier-disque JSON persistant :

```text
code/data/esinos.disk.json
```

Le menu crée ce fichier à sa première utilisation. Il représente un disque
virtuel : créer `notes.txt` dans ESINOS ne crée pas un fichier de ce nom sur
l’ordinateur.

Le modèle contient la taille d’un bloc, une liste de blocs et une table d’inodes.
Un bloc libre vaut `null`. Un bloc occupé contient une liste d’octets. Chaque
inode occupé indique le numéro du fichier, son nom, sa taille et ses blocs.
Le nom est conservé directement dans l’inode pour simplifier ce modèle.

Les opérations disponibles sont :

- **Créer** : encoder le texte en UTF-8, choisir un inode libre et les premiers blocs libres, puis sauvegarder.
- **Lire** : suivre les blocs de l’inode et réassembler tous les octets avant le décodage UTF-8.
- **Supprimer** : après confirmation `oui`, libérer les blocs et l’emplacement d’inode.
- **Table d’inodes** : afficher les cases libres et occupées avec les numéros de blocs associés.

Par défaut, le disque dispose de **64 blocs de 64 octets et de 16 inodes**,
soit 4 096 octets de capacité logique pour les contenus. Le fichier JSON peut
être plus grand, car il contient aussi la représentation textuelle et les
métadonnées.

Les noms sont uniques, un fichier vide peut occuper un inode sans bloc, et une
création est refusée s’il manque des blocs ou un inode. La validation contrôle
les références et les tailles. Les sauvegardes publient une image complète
par remplacement atomique ; une initialisation refuse d’écraser une image
existante.

## Démonstration et résultats de référence

Depuis `code`, lancer :

```bash
python3 -m esinos demo
```

Le même scénario est rejoué à chaque exécution : les quatre Gantt CPU, leurs
mesures, la trace FIFO et la comparaison mémoire, les traductions et l’EAT,
puis la création, lecture et suppression d’un fichier avec sa table d’inodes.
Le disque de démonstration est temporaire et ne modifie pas le disque de travail.

### CPU

Les processus sont P1 `(AT=0, BT=7, priorité=2)`, P2 `(2,4,1)`,
P3 `(4,1,3)` et P4 `(5,4,2)`. Le quantum Round Robin vaut `2`.

| Politique | Attente moyenne | Séjour moyen |
| --- | ---: | ---: |
| FCFS | 4,75 | 8,75 |
| SJF | 4,00 | 8,00 |
| Round Robin | 5,00 | 9,00 |
| Priority | 5,50 | 9,50 |

### Mémoire et fichiers

| Expérience | Résultat attendu |
| --- | --- |
| Références `7,0,1,2,0,3,0,4,2,3,0,3,2`, trois cadres | FIFO : 10 défauts ; LRU : 9 ; Optimal : 7 |
| Pages de 64 octets, page 1 dans le cadre 2 | Adresse 70 → 134 ; adresse 75 → 139 |
| Suite d’adresses de la démo, TLB de deux entrées | 1 hit sur 8 ; EAT de 197,50 ns pour TLB=10 ns et mémoire=100 ns |
| `notes.txt`, 40 octets dans des blocs de 16 | Inode 1, blocs `[0, 1, 2]`, puis libération après suppression |

## Organisation du code

```text
esinos/
├── README.md
├── report.pdf
└── code/
    ├── Makefile
    ├── esinos/
    │   ├── __init__.py
    │   ├── __main__.py
    │   ├── cli.py
    │   ├── menus.py
    │   ├── entrees.py
    │   ├── sorties.py
    │   ├── affichage.py
    │   ├── scheduler.py
    │   ├── memory.py
    │   └── filesystem.py
    └── tests/
```

| Module | Responsabilité |
| --- | --- |
| `scheduler.py` | Appliquer les quatre politiques CPU et calculer CT, WT et TAT |
| `memory.py` | Calculer le remplacement des pages, la traduction, le TLB et l’EAT |
| `filesystem.py` | Valider le disque JSON, allouer les blocs et manipuler les fichiers |
| `entrees.py` | Lire et valider les valeurs saisies |
| `sorties.py` et `affichage.py` | Présenter les mesures, les tableaux et les Gantt |
| `menus.py` | Conserver les exemples et les données des sous-menus, lancer la démo |
| `cli.py` et `__main__.py` | Ouvrir le menu ou la démonstration depuis le terminal |

Les calculs renvoient des données sans dépendre de l’affichage. Cette séparation
permet de tester les algorithmes directement et de présenter leurs résultats
dans les menus.

## Tests et vérification

Depuis le dossier `code` :

```bash
python3 -m unittest discover -s tests -v
```

La suite comporte **40 tests**. Elle couvre les exemples de référence, les
saisies du menu, les types et valeurs invalides, les égalités et périodes
inactives du CPU, les frontières de quantum, les pages et cadres zéro, les
capacités du disque, l’UTF-8 partagé entre blocs et les échecs d’écriture.

Des références indépendantes et des cas exhaustifs courts vérifient aussi
les calculs CPU, le remplacement et le TLB. La commande précédente exécute
ces vérifications localement.

Les raccourcis facultatifs sont :

```bash
make run
make demo
make test
```

## Livrables et présentation

Le dépôt fournit le code commenté dans `code/`, ce README et le
[rapport technique de quatre pages](report.pdf), qui présente l’approche,
les difficultés, les résultats et les liens avec le cours.

Pour la remise finale, le groupe ajoute **`demo.mp4` à la racine du dépôt**.
Cette vidéo doit être enregistrée caméra ouverte et montrer les Gantt
FCFS/SJF/RR, l’éviction FIFO puis la comparaison avec LRU, et les opérations
du bonus à inodes. Elle doit également expliquer le code et les concepts
présentés.
