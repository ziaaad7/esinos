# ESINOS - mini-noyau simulé

ESINOS 3.1 simule l'ordonnancement CPU, la mémoire virtuelle et le bonus de
système de fichiers à inodes. Le programme utilise uniquement Python 3.9 ou
plus récent et sa bibliothèque standard.

## Installation et lancement

Au premier téléchargement :

```bash
git clone https://github.com/ziaaad7/esinos.git
cd esinos
cd code
python3 -m esinos
```

Avec un ZIP, décompressez-le et ouvrez le dossier du projet avant `cd code`.
Sur ton Mac, si le projet est déjà dans Documents :

```bash
cd ~/Documents/esinos/code
python3 -m esinos
```

## Utilisation

| Choix | Simulation |
| --- | --- |
| 1 | CPU : FCFS, SJF, Round Robin, Priority et comparaison |
| 2 | Pages : FIFO, LRU, Optimal et comparaison |
| 3 | Traduction d'adresses, TLB et EAT |
| 4 | Fichiers à inodes et carte du disque |
| 5 | Démonstration complète |
| 6 | EAT avec défauts de page |
| 0 | Quitter |

Les sous-menus commencent avec un exemple. Entrée conserve une valeur proposée.
Le mode Résumé affiche les résultats ; Expliqué ajoute les raisons ; Pas à pas
attend Entrée entre deux décisions. Dans ce dernier mode, t affiche la suite
et 0 revient au menu.

Pour rejouer les exemples sans saisie :

```bash
python3 -m esinos demo --explain
```

## Organisation et guides

- `scheduler.py` et `memory.py` : calculs des simulations.
- `filesystem.py` et `disque_binaire.py` : fichiers et image disque.
- `menus.py`, `entrees.py` et `cli.py` : navigation et commandes.
- `affichage.py`, `sorties.py`, `pedagogie.py`, `carte_disque.py` : résultats lisibles.

Les guides détaillent [le CPU](docs/01-ordonnancement.md),
[la mémoire](docs/02-memoire.md) et [les fichiers](docs/03-fichiers.md).
`python3 -m esinos --help` présente aussi les commandes du Terminal.

## Vérification et livrables

Depuis le dossier code :

```bash
python3 -m unittest discover -s tests -v
```

Les tests vérifient les calculs, les cas limites et les parcours du menu.
`make run`, `make demo` et `make test` sont des raccourcis facultatifs.

Le dépôt contient le code, les guides et le [rapport technique](report.pdf).
Le groupe ajoute sa vidéo `demo.mp4`, enregistrée caméra ouverte, à la racine
pour la remise.
