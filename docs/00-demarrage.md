# Démarrage ESINOS 3.0.0

## Ce que lance le programme

ESINOS est un atelier de simulation. Il calcule et affiche des décisions
d’ordonnancement, de mémoire et de système de fichiers. Il ne démarre pas un
noyau ni une machine virtuelle.

Le projet demande Python 3.9 ou plus récent et n’installe aucune dépendance
externe.

## Installation

Dans le Terminal, placez-vous dans le dossier où vous voulez récupérer le
projet, puis lancez les quatre commandes ci-dessous.

~~~bash
git clone https://github.com/ziaaad7/esinos.git
cd esinos
cd code
python3 -m esinos
~~~

Sur macOS, si le projet existe déjà dans Documents :

~~~bash
cd ~/Documents/esinos/code
python3 -m esinos
~~~

Pour un ZIP, décompressez-le puis ouvrez son dossier. Le nom obtenu depuis
GitHub est souvent esinos-main, pas esinos. Dans ce cas, adaptez simplement le
premier cd avant de taper cd code.

## Menu principal

| Choix | Ouvre |
| --- | --- |
| 1 | Le sous-menu CPU |
| 2 | Le sous-menu remplacement de pages |
| 3 | Le sous-menu traduction, TLB et EAT TLB |
| 4 | Le sous-menu système de fichiers |
| 5 | La démonstration reproductible |
| 6 | Le calcul EAT avec défauts de page |
| 0 | La sortie du programme |

Les exemples CPU, remplacement et traduction sont préchargés. Une réponse vide
conserve la valeur entre crochets.

Quand un calcul propose les trois modes, Résumé donne le résultat final,
Expliqué donne toutes les raisons et Pas à pas s’arrête après chaque raison.
Dans ce dernier mode, Entrée passe à la suivante, t affiche le reste et 0
retourne au sous-menu.

## Démonstration et aide

~~~bash
python3 -m esinos --version
python3 -m esinos --help
python3 -m esinos demo
python3 -m esinos demo --explain
~~~

La variante --explain ne demande pas de touche : elle déroule les explications
de Round Robin, FIFO et TLB automatiquement. La démonstration crée son disque
de test dans un dossier temporaire.

## Commandes courantes

Les commandes suivantes partent toutes du dossier code.

~~~bash
python3 -m esinos scheduler --algorithm fcfs \
  --processes "P1:0:7:2,P2:2:4:1"

python3 -m esinos memory --algorithm lru --frames 3 \
  --references "7,0,1,2,0,3,0"

python3 -m esinos translate --page-size 64 --page-table "0:5,1:2,2:7,3:1" \
  --addresses "5,70,75,130,5,195,70,260"

python3 -m esinos eat --fault-rate 0.001 --memory-time 100 \
  --fault-time 1000000
~~~

La dernière commande donne 1099.90 ns. Les paramètres EAT sont des
nanosecondes dans les exemples, mais le modèle reste correct dans toute unité
commune.

Le disque par défaut est data/esinos.disk.img. L’ancien JSON est lisible sans
être réécrit. Pour demander une migration explicite qui conserve la source :

~~~bash
python3 -m esinos fs --disk ancien.json migrate nouveau.img
~~~

Le futur guide complet est [03-fichiers.md](03-fichiers.md).

## Vérifier

~~~bash
python3 -m unittest discover -s tests -v
make test
~~~

Le résultat de cette commande est l’autorité pour le nombre de tests verts.

