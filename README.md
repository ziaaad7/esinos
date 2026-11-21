# ESINOS 3.0.0

ESINOS est un simulateur pédagogique en Python 3 pour l’ordonnancement CPU, la
mémoire virtuelle et le système de fichiers à inodes. Le code emploie des
fonctions, listes, dictionnaires et boucles. Il simule des mécanismes du cours
dans l’espace utilisateur : ce n’est ni un noyau binaire ni un système
d’exploitation installé sur l’ordinateur.

## Démarrage rapide

Python 3.9 ou plus récent suffit. Pour cloner le dépôt, exécutez exactement ces
quatre lignes.

~~~bash
git clone https://github.com/ziaaad7/esinos.git
cd esinos
cd code
python3 -m esinos
~~~

Sur un Mac où le dépôt existe déjà dans Documents :

~~~bash
cd ~/Documents/esinos/code
python3 -m esinos
~~~

Avec un ZIP, décompressez-le, ouvrez son dossier puis tapez cd code. Un ZIP
GitHub peut s’appeler esinos-main : adaptez le chemin au nom réel du dossier.

## Parcours

| Menu | Fonction |
| --- | --- |
| 1 | Ordonnancement CPU |
| 2 | Remplacement de pages |
| 3 | Traduction, TLB et EAT TLB |
| 4 | Système de fichiers à inodes |
| 5 | Démonstration |
| 6 | EAT avec défauts de page |
| 0 | Quitter |

Les sous-menus CPU et mémoire utilisent d’abord les jeux de données proposés.
Entrée conserve une valeur entre crochets. Les calculs peuvent proposer Résumé,
Expliqué ou Pas à pas. En pas à pas, Entrée avance, t affiche la suite et 0
revient au sous-menu.

## Commandes utiles

Depuis code :

~~~bash
python3 -m esinos --version
python3 -m esinos demo
python3 -m esinos demo --explain
python3 -m esinos eat --fault-rate 0.001 --memory-time 100 --fault-time 1000000
~~~

La dernière commande affiche un EAT de 1099.90 ns. Le modèle TLB précédent ne
change pas : avec le scénario fourni, il donne 1 hit sur 8 et 197.50 ns.

~~~bash
python3 -m esinos scheduler --algorithm rr --quantum 2 \
  --processes "P1:0:7:2,P2:2:4:1,P3:4:1:3,P4:5:4:2" --explain

python3 -m esinos memory --algorithm fifo --frames 3 \
  --references "7,0,1,2,0,3,0,4,2,3,0,3,2" --explain

python3 -m esinos translate --page-size 64 --page-table "0:5,1:2,2:7,3:1" \
  --addresses "5,70,75,130,5,195,70,260" --tlb-size 2 --explain
~~~

Le disque par défaut est data/esinos.disk.img, une image binaire. Les anciennes
images JSON restent lisibles et ne sont jamais remplacées par une lecture. Pour
créer une copie binaire distincte d’un ancien disque :

~~~bash
python3 -m esinos fs --disk ancien.json migrate nouveau.img
~~~

Le menu fichiers propose aussi l’option 10 pour cette migration. Le format
binaire réserve avant les données un superbloc, un bitmap des données, les
inodes et le répertoire. Son CRC32 contrôle la cohérence, sans être un mécanisme
cryptographique.

## Guides

- [00 — Démarrage et commandes](docs/00-demarrage.md)
- [01 — Ordonnancement CPU](docs/01-ordonnancement.md)
- [02 — Mémoire, TLB et les deux EAT](docs/02-memoire.md)
- [03 — Système de fichiers](docs/03-fichiers.md) — format, carte, persistance et migration
- [04 — Architecture et tests](docs/04-architecture-tests.md)

## Vérifier

~~~bash
python3 -m unittest discover -s tests -v
make test
~~~

La version 3.0.0 comprend **88 tests automatisés**, avec des oracles indépendants,
des parcours interactifs et des contrôles de corruption et de migration.
Le [workflow de validation](.github/workflows/tests.yml) les rejoue sur Linux,
Windows et macOS. Les résultats sont visibles dans l’onglet Actions de GitHub.

## Livrables

Le dépôt contient le code, les guides et le [rapport technique](report.pdf).
Le groupe enregistre la démonstration avec caméra ouverte, puis ajoute
`demo.mp4` à la racine pour la remise. Le scénario `demo --explain` fournit
un déroulement reproductible pour cet enregistrement.
