# ESINOS - mini-noyau simulé

ESINOS est un simulateur pédagogique écrit en Python avec des fonctions,
des listes et des dictionnaires. Il permet de saisir ses données et
d'observer les décisions d'ordonnancement, de pagination et d'allocation
de fichiers. Python 3.9 ou plus récent suffit. Le code utilise la
bibliothèque standard.

## Télécharger et lancer

Au premier téléchargement avec Git, ouvrez le Terminal dans le dossier
où vous souhaitez installer le projet.

```bash
git clone https://github.com/ziaaad7/esinos.git
cd esinos
cd code
python3 -m esinos
```

Si vous avez téléchargé un ZIP, décompressez-le et ouvrez son dossier
avant de taper `cd code`. Si le projet se trouve déjà dans Documents
sur votre Mac, utilisez directement ces commandes.

```bash
cd ~/Documents/esinos/code
python3 -m esinos
```

Le menu propose les parcours suivants.

| Choix | Simulation |
| --- | --- |
| 1 | CPU avec FCFS, SJF, Round Robin et Priority |
| 2 | Remplacement de pages avec FIFO, LRU et Optimal |
| 3 | Traduction d'adresses, TLB et EAT |
| 4 | Bonus officiel du disque virtuel à inodes |
| 5 | Démonstration complète |
| 0 | Quitter |

Appuyez sur Entrée pour garder une valeur proposée entre crochets.
Dans les choix CPU et mémoire, sélectionnez un algorithme par son numéro
ou par son nom. La démo peut aussi être lancée directement depuis `code/`.

```bash
python3 -m esinos demo
```

## Ordonnancement CPU

Un processus contient son nom, son instant d'arrivée AT, sa durée CPU BT
et sa priorité numérique. Dans le menu, vous pouvez conserver les
processus proposés ou saisir une liste comme celle-ci.

```text
P1:0:7:2,P2:2:4:1,P3:4:1:3,P4:5:4:2
```

La priorité est facultative dans une commande et vaut alors zéro.
FCFS fait passer le premier arrivé. SJF prend la plus courte durée parmi
les processus prêts. Priority choisit le plus petit numéro de priorité.
Ces trois politiques sont non préemptives. Round Robin partage le CPU
avec un quantum positif. Les arrivées à la fin d'une tranche sont ajoutées
à la file avant la réinsertion du processus interrompu.

Le Gantt contient les tranches d'exécution et les périodes `IDLE`.
Le tableau donne PID, AT, BT, Prio, Fin (CT), Attente et Séjour.

```text
séjour = fin - arrivée
attente = séjour - durée CPU
```

Le code du calcul se trouve dans `code/esinos/scheduler.py`.
Un processus y est un dictionnaire. `ordonnancer` renvoie le Gantt
et les lignes du tableau. La file de Round Robin est une liste.

## Mémoire virtuelle

`code/esinos/memory.py` contient les fonctions de remplacement,
de traduction et de calcul de l'EAT.

- `remplacer` suit une suite de pages et montre les cadres, les hits,
  les défauts et la victime de chaque accès.
- `traduire` traite une suite d'adresses avec une table page-cadre et
  un TLB à remplacement LRU. Le cache vit pendant cette suite.
- `calculer_eat` fait la moyenne des coûts d'accès selon le taux
  de hit. Le modèle exclut le délai de chargement depuis le stockage.

```text
page = adresse // taille_page
déplacement = adresse % taille_page
physique = cadre * taille_page + déplacement
EAT = temps_TLB + (2 - taux_hit) * temps_mémoire
```

Un cadre 0 est valide. Une page absente de la table donne une adresse
physique à `None`. Cet accès compte comme un miss dans le ratio TLB.

## Bonus officiel des fichiers à inodes

Le module `code/esinos/filesystem.py` conserve les fichiers virtuels dans
une image disque JSON. Les inodes et les blocs sont représentés avec
des listes et des dictionnaires. Les opérations sont des fonctions
comme `creer_fichier`, `lire_fichier` et `supprimer_fichier`.

Les images ESINOS existantes restent lisibles. Les écritures utilisent
le format ESINOS version 1 et ses blocs en Base64. Le menu charge le
disque à `code/data/esinos.disk.json`. L'initialisation refuse
d'écraser une image. Le reformatage dans le menu demande une confirmation.

## Commandes reproductibles

Ces exemples s'exécutent depuis le dossier `code/`.

```bash
python3 -m esinos scheduler --algorithm rr --quantum 2 --processes "P1:0:7:2,P2:2:4:1,P3:4:1:3,P4:5:4:2"
python3 -m esinos memory --algorithm fifo --frames 3 --references "7,0,1,2,0,3,0,4,2,3,0,3,2"
python3 -m esinos translate --page-size 64 --page-table "0:5,1:2,2:7,3:1" --addresses "5,70,75,130,5,195,70,260"
python3 -m esinos fs --disk data/exemple.disk.json --blocks 12 --block-size 16 --inodes 4 init
python3 -m esinos fs --disk data/exemple.disk.json create notes.txt "Bonjour ESINOS"
python3 -m esinos fs --disk data/exemple.disk.json inodes
python3 -m esinos fs --disk data/exemple.disk.json read notes.txt
python3 -m esinos fs --disk data/exemple.disk.json delete notes.txt
```

## Résultats de la démonstration

| Algorithme ou mesure | Résultat |
| --- | --- |
| FCFS, attente / séjour moyens | 4,75 / 8,75 |
| SJF, attente / séjour moyens | 4,00 / 8,00 |
| Round Robin q=2, attente / séjour moyens | 5,00 / 9,00 |
| Priority, attente / séjour moyens | 5,50 / 9,50 |
| Défauts FIFO / LRU / Optimal | 10 / 9 / 7 |
| Traduction de 75 | Adresse 139, hit TLB |
| TLB et EAT | 1 hit sur 8 et 197,50 ns |
| Fichier de démo | 40 octets, inode 1 et blocs 0, 1, 2 |

La démo crée une image temporaire pour ses fichiers. Le menu conserve
l'image interactive après la fermeture du programme.

## Vérifier le code

Depuis `code/`, lancez la suite de tests.

```bash
python3 -m unittest discover -s tests -v
```

Avec `make`, les raccourcis `make run`, `make demo` et `make test`
appellent les mêmes commandes.

## Organisation

```text
code/
  esinos/
    __main__.py      lance cli.main
    cli.py           menu, commandes et affichage
    scheduler.py     fonctions des quatre politiques CPU
    memory.py        remplacement, traduction, TLB et EAT
    filesystem.py    image, inodes et blocs
  tests/             vérification des algorithmes et commandes
  Makefile           raccourcis facultatifs
```

Le programme calcule sur des données simulées. Il utilise un CPU, des
durées abstraites et un seul burst par processus. Le coût de changement
de contexte est omis. Le disque est prévu pour une session de modification
à la fois.

## Livrables

Le dépôt contient `code/`, ce `README.md` et `report.pdf`.
Le groupe enregistre sa vidéo caméra ouverte et ajoute `demo.mp4`
à la racine pour la remise.
