# ESINOS - mini-noyau simulé

ESINOS 3.3 est une simulation en espace utilisateur, écrite en Python.

- CPU : FCFS, SJF, Round Robin et Priority, Gantt et attentes/séjours moyens ;
- mémoire : pagination, traduction logique vers physique, FIFO, LRU, Optimal, TLB et EAT ;
- bonus prévu par le sujet : fichiers à inodes persistants sur un fichier-disque.

## Installation et lancement

Python 3.9 ou plus récent suffit. Aucune bibliothèque externe n'est nécessaire.

Au premier téléchargement :

```bash
git clone https://github.com/ziaaad7/esinos.git
cd esinos
cd code
python3 -m esinos
```

Avec un ZIP, ouvrez le dossier décompressé du projet, puis son dossier `code`.
Sur le Mac où le projet est déjà dans Documents :

```bash
cd ~/Documents/esinos/code
python3 -m esinos
```

## Menu

| Choix | Fonction |
| --- | --- |
| 1 | Ordonnancement CPU |
| 2 | Remplacement de pages |
| 3 | Traduction, TLB et EAT |
| 4 | Bonus : créer, lire, supprimer et afficher la table d'inodes |
| 5 | Démonstration des fonctions du sujet |
| 0 | Quitter |

Le sous-menu CPU permet de choisir une politique, comparer les quatre,
saisir des processus ou restaurer l'exemple. Les valeurs demandées sont le
nom, l'arrivée AT, la durée BT et la priorité. CT, attente et séjour sont calculés.
Round Robin demande aussi son quantum. Entrée conserve une valeur proposée.

Le sous-menu mémoire permet de modifier les références et le nombre de cadres.
Son tableau montre chaque accès, la page évincée et les cadres obtenus : c'est
la trace étape par étape demandée pour la démonstration FIFO. La comparaison
emploie les mêmes données pour FIFO, LRU et Optimal.

La traduction permet de saisir les adresses, la taille de page, la table
`page:cadre`, la capacité TLB et les temps en ns. Le cadre 0 est valide ; une
page absente de la table provoque un défaut de page.

Le bonus stocke les blocs et les inodes dans `code/data/esinos.disk.json`.
Ce JSON représente le disque simulé ; créer un fichier virtuel ne crée pas
un fichier de même nom sur votre ordinateur. La suppression demande `oui`.

## Conventions et résultats de référence

FCFS, SJF et Priority sont non préemptifs. Le plus petit numéro de priorité
est le plus urgent. Les égalités sont départagées par arrivée puis nom.
Dans Round Robin, les arrivées en fin de tranche entrent avant la réinsertion
du processus interrompu. Le Gantt est proportionnel lorsque les noms et les instants tiennent dans
le Terminal ; sinon un schéma indique les bornes exactes. Attente = CT - AT - BT ; séjour = CT - AT.

Avec P1(0,7,p2), P2(2,4,p1), P3(4,1,p3), P4(5,4,p2) et un quantum de 2 :

| Politique | Attente moyenne | Séjour moyen |
| --- | ---: | ---: |
| FCFS | 4,75 | 8,75 |
| SJF | 4,00 | 8,00 |
| Round Robin | 5,00 | 9,00 |
| Priority | 5,50 | 9,50 |

La suite `7,0,1,2,0,3,0,4,2,3,0,3,2` avec trois cadres produit
10 défauts FIFO, 9 LRU et 7 Optimal. Optimal connaît les références futures.

Le TLB suit LRU. L'EAT vaut `temps_TLB + (2 - taux_hit) * temps_mémoire` :
un hit nécessite un accès mémoire, un miss en nécessite deux. Ce modèle ne
compte pas le chargement depuis le disque d'une page absente. La démonstration
donne 1 hit sur 8 accès et 197,50 ns avec 10 ns de TLB et 100 ns de mémoire.

## Vérification et livrables

Depuis `code`, rejouer la démonstration et les tests :

```bash
python3 -m esinos demo
python3 -m unittest discover -s tests -v
```

Les tests couvrent les calculs, les cas limites, les saisies du menu et la
persistance du disque. `make run`, `make demo` et `make test` sont facultatifs.
Le code sépare les calculs (`scheduler.py`, `memory.py`, `filesystem.py`),
les saisies et menus, et l'affichage des résultats.

Le [rapport](report.pdf) présente l'approche, les difficultés et les résultats.
Pour la remise, le groupe ajoute `demo.mp4` à la racine : vidéo caméra ouverte
montrant FCFS/SJF/RR, l'éviction FIFO puis LRU, et les opérations sur les inodes.
