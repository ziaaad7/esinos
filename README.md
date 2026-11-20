# ESINOS 2.1.0 — mini-noyau simulé

ESINOS est un simulateur pédagogique de systèmes d’exploitation écrit en
Python 3. Il rend visibles l’ordonnancement CPU, la mémoire virtuelle et le
bonus officiel de système de fichiers à inodes, avec des fonctions, des
boucles, des listes et des dictionnaires de la bibliothèque standard.

Le programme simule des mécanismes du cours dans l’espace utilisateur. Ce
n’est ni un noyau binaire ni un système d’exploitation installé sur la machine.

## Installer et lancer

Python 3.9 ou plus récent suffit. Depuis le dossier où vous voulez cloner le
dépôt, lancez les commandes suivantes.

~~~bash
git clone https://github.com/ziaaad7/esinos.git
cd esinos
cd code
python3 -m esinos
~~~

Avec un ZIP, décompressez-le, ouvrez le dossier du projet puis tapez `cd code`.
Un ZIP téléchargé depuis GitHub peut se nommer `esinos-main` : adaptez la
commande précédente au nom réel du dossier.

Si le dépôt est déjà présent dans Documents sur votre Mac, ouvrez directement
le même projet.

~~~bash
cd ~/Documents/esinos/code
python3 -m esinos
python3 -m esinos --version
~~~

## Menu et jeux de données préchargés

Les sous-menus CPU, mémoire et traduction commencent avec un jeu de données
préchargé. Le sous-menu disque ouvre son image configurée et l’initialise si
elle n’existe pas. Appuyer sur Entrée garde une valeur proposée entre crochets.

| Choix | Parcours |
| --- | --- |
| 1 | Ordonnancement CPU |
| 2 | Remplacement de pages |
| 3 | Traduction d’adresses, TLB et EAT |
| 4 | Système de fichiers à inodes |
| 5 | Démonstration complète |
| 0 | Quitter |

### Modes Résumé, Expliqué et Pas à pas

Après le choix d’un algorithme CPU, mémoire ou traduction, le programme propose
les modes Résumé, Expliqué et Pas à pas.

- Résumé affiche le Gantt ou le tableau final.
- Expliqué déroule automatiquement les décisions qui ont produit le résultat.
- Pas à pas affiche une décision puis attend une commande. Entrée montre
  l’étape suivante, t affiche le reste et 0 revient au sous-menu.

Les explications sont construites à partir des traces calculées. Elles ne
modifient donc ni les algorithmes ni leurs résultats.

### 1. Ordonnancement CPU

Le sous-menu commence avec quatre processus préchargés. Les choix 1 à 4 lancent
FCFS, SJF, Round Robin et Priority. Le choix 5 compare les quatre politiques
sur les mêmes processus et demande le quantum de Round Robin. Le choix 6 ouvre
un assistant de saisie, processus par processus, pour le nom, AT, BT et la
priorité. Le choix 7 restaure l’exemple.

Les colonnes finales sont PID, AT, BT, Prio, Fin (CT), Attente et Séjour.
FCFS, SJF et Priority sont non préemptifs. Round Robin utilise un quantum
positif et une file d’attente.

~~~text
séjour = CT - AT
attente = séjour - BT
~~~

### 2. Remplacement de pages

Le jeu préchargé contient la suite 7,0,1,2,0,3,0,4,2,3,0,3,2 avec trois
cadres. Les choix 1, 2 et 3 lancent FIFO, LRU et Optimal. Le choix 4 compare
les trois résultats. Le choix 5 personnalise la suite et le nombre de cadres.
Le choix 6 rétablit l’exemple.

Chaque trace indique le hit ou défaut, la victime éventuelle et les cadres. En
mode expliqué, FIFO justifie la page chargée la première, LRU la page utilisée
la moins récemment et Optimal la prochaine utilisation la plus lointaine.

### 3. Traduction, TLB et EAT

Le jeu préchargé utilise des pages de 64 octets, une table page→cadre et un TLB
de capacité 2. Le choix 1 lance le calcul. Le choix 2 modifie les adresses, la
taille de page, la table, la capacité du TLB et les deux temps d’accès. Le
choix 3 rétablit l’exemple.

~~~text
page = adresse // taille_page
déplacement = adresse % taille_page
adresse physique = cadre * taille_page + déplacement
EAT = temps_TLB + (2 - taux_hit) * temps_mémoire
~~~

Le TLB emploie LRU. Le cadre 0 est valide. Une page absente donne cadre=None et
une adresse physique None. Elle compte comme un miss pour l’EAT, dont la
pénalité de chargement depuis le stockage est exclue.

### 4. Bonus officiel du système de fichiers

Le menu travaille sur une image JSON persistante. Il propose créer, lire,
supprimer, lister, afficher les inodes, afficher l’état et reformater. Le choix
8 affiche une carte des blocs libres et occupés. Le choix 9 suit un fichier
depuis son inode vers ses blocs et son contenu UTF-8 reconstitué.

L’initialisation ne remplace pas une image existante. Le reformatage demande une
confirmation. Les blocs sont stockés au format ESINOS version 1 avec leur
contenu encodé en Base64.

## Démonstration reproductible

Depuis code, la démonstration résumée exécute les mêmes scénarios que le menu.

~~~bash
python3 -m esinos demo
~~~

La variante suivante active automatiquement le mode Expliqué. Elle détaille
Round Robin, FIFO et la traduction sans demander de touche à chaque étape. Le
bonus affiche aussi le parcours de notes.txt et sa carte de blocs.

~~~bash
python3 -m esinos demo --explain
~~~

| Mesure | Résultat |
| --- | --- |
| Attente / séjour moyens FCFS | 4,75 / 8,75 |
| Attente / séjour moyens SJF | 4,00 / 8,00 |
| Attente / séjour moyens RR, quantum 2 | 5,00 / 9,00 |
| Attente / séjour moyens Priority | 5,50 / 9,50 |
| Défauts FIFO / LRU / Optimal | 10 / 9 / 7 |
| TLB et EAT | 1 hit sur 8 et 197,50 ns |
| Fichier de démo | inode 1, blocs 0, 1, 2 et 40 octets |

La démo crée son image dans un dossier temporaire. Le menu interactif garde son
image entre les lancements.

## Commandes terminal réelles

Les commandes suivantes s’exécutent depuis code. L’option --explain est
disponible pour demo, scheduler, memory et translate.

~~~bash
python3 -m esinos scheduler --algorithm rr --quantum 2 \
  --processes "P1:0:7:2,P2:2:4:1,P3:4:1:3,P4:5:4:2" --explain

python3 -m esinos memory --algorithm fifo --frames 3 \
  --references "7,0,1,2,0,3,0,4,2,3,0,3,2" --explain

python3 -m esinos translate --page-size 64 --page-table "0:5,1:2,2:7,3:1" \
  --addresses "5,70,75,130,5,195,70,260" --tlb-size 2 --explain
~~~

Voici un petit disque de travail, puis les commandes pour le visualiser et
suivre un fichier.

~~~bash
python3 -m esinos fs --disk data/exemple.disk.json \
  --blocks 12 --block-size 16 --inodes 4 init
python3 -m esinos fs --disk data/exemple.disk.json create notes.txt "Bonjour ESINOS"
python3 -m esinos fs --disk data/exemple.disk.json map
python3 -m esinos fs --disk data/exemple.disk.json explain notes.txt
python3 -m esinos fs --disk data/exemple.disk.json read notes.txt
python3 -m esinos fs --disk data/exemple.disk.json delete notes.txt
~~~

Les autres actions de disque sont list, inodes et status.

## Organisation du code

~~~text
code/
  esinos/
    __main__.py      lance cli.main
    cli.py           menu, sous-menus, commandes et démonstration
    scheduler.py     FCFS, SJF, RR, Priority et mesures
    memory.py        FIFO, LRU, Optimal, TLB et EAT
    filesystem.py    image JSON, inodes, blocs et Base64
    affichage.py     Gantt, tableaux ASCII et explications CPU
    pedagogie.py     explications des traces mémoire et TLB
    carte_disque.py  carte des blocs et parcours d’un fichier
  tests/             tests des algorithmes, traces et commandes
  Makefile           raccourcis facultatifs
~~~

affichage.py transforme le Gantt et les mesures en texte lisible, puis produit
les explications CPU. pedagogie.py reconstruit les états avant et après des
traces FIFO, LRU, Optimal et TLB. carte_disque.py lit l’image par l’interface
publique du système de fichiers pour construire une carte ou un parcours, sans
modifier le JSON.

Les modules de calcul gardent une syntaxe accessible aux débutants. Les
résultats sont des données simulées, pas des appels au noyau de l’ordinateur.

## Vérifier le projet et remettre

Depuis code, exécutez les tests.

~~~bash
python3 -m unittest discover -s tests -v
make run
make demo
make test
~~~

Le dépôt contient code, ce README.md et report.pdf. Le groupe ajoute demo.mp4 à
la racine pour la remise. La vidéo doit être enregistrée caméra ouverte.
