# Système de fichiers à inodes

Le choix 4 du menu principal ouvre le disque persistant. La première ouverture
crée data/esinos.disk.img dans le dossier code. Les ouvertures suivantes
retrouvent les fichiers déjà enregistrés.

| Choix | Action |
| --- | --- |
| 1, 2, 3 | Créer, lire ou supprimer un fichier |
| 4, 5, 6 | Lister les fichiers, les inodes ou l'état du disque |
| 7 | Reformater après confirmation |
| 8 | Afficher la carte des blocs |
| 9 | Suivre un fichier de son nom jusqu'à ses blocs |
| 10 | Copier une ancienne image JSON ouverte vers un nouveau binaire |
| 0 | Retour |

## Organisation du disque

| Zone | Rôle |
| --- | --- |
| S : superbloc | Signature, version, géométrie et CRC32 |
| B : bitmap | Occupation des blocs de données |
| I : inodes | Taille des fichiers et pointeurs directs |
| R : répertoire | Correspondance entre noms et numéros d'inodes |
| Données | Contenu des fichiers, réparti dans des blocs de taille fixe |

Les zones commencent sur une frontière de bloc. Le nombre de blocs choisi
pour le disque désigne les données ; les métadonnées sont réservées avant.
La carte et le suivi distinguent bloc logique et position physique :

```text
bloc physique = data_start + bloc logique
position en octets = bloc physique × taille_bloc
```

Dans l'exemple de démonstration, les 12 blocs de données font 16 octets et
la table contient 4 inodes. Les données commencent au bloc physique 37.
Un texte de 40 octets utilise les blocs logiques 0, 1 et 2.

## Création, lecture et suppression

La création choisit le premier inode et les premiers blocs libres. Le contenu
est encodé en UTF-8 ; sa taille se mesure en octets. La lecture rassemble les
morceaux avant de décoder le texte. Une lettre accentuée peut ainsi traverser
une frontière de bloc. Un fichier vide prend un inode sans bloc de données.
La suppression libère ces emplacements pour un prochain fichier.

Un nom possède 1 à 64 caractères ASCII, commence par une lettre ou un chiffre,
et peut ensuite contenir des points, tirets ou tirets bas. Les doublons,
les capacités dépassées et les fichiers absents sont refusés.

## Conservation de l'image

Le chargement contrôle la cohérence de l'image et ses CRC32. Une modification
est préparée dans un fichier temporaire, synchronisée, puis publiée en une
opération. L'initialisation et la copie d'un JSON refusent d'écraser une cible.
Le reformatage du menu demande confirmation.

Le format binaire reste compatible avec ESINOS 3.0. Les anciens JSON restent
lisibles et gardent leur format quand ils sont modifiés. Si seul l'ancien
data/esinos.disk.json existe, le menu l'ouvre et son choix 10 propose une
copie .img en conservant l'original.

filesystem.py expose les opérations sur les fichiers. disque_binaire.py
partage leur validation et transforme le modèle en octets. Le disque est
prévu pour une seule session de modification à la fois.
