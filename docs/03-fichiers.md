# Système de fichiers à inodes

Depuis le dossier code, un exemple reproductible :

```bash
python3 -m esinos fs --disk data/exemple.img --blocks 12 --block-size 16 --inodes 4 init
python3 -m esinos fs --disk data/exemple.img create notes.txt "Bonjour ESINOS"
python3 -m esinos fs --disk data/exemple.img map
python3 -m esinos fs --disk data/exemple.img explain notes.txt
python3 -m esinos fs --disk data/exemple.img read notes.txt
python3 -m esinos fs --disk data/exemple.img delete notes.txt
```

init attend un chemin neuf. Une image persistante se réouvre sans l'initialiser.

## Le bonus système de fichiers

Le système de fichiers range des fichiers virtuels dans une image disque
persistante. ESINOS 3 crée une image binaire .img : ses octets représentent
un petit disque. Les fichiers virtuels restent disponibles après fermeture.

Le programme utilise des dictionnaires en mémoire pour décrire les inodes et
les blocs. Le module disque_binaire transforme ce modèle en octets, puis
fait l'opération inverse à l'ouverture.

| Niveau | Élément | Rôle |
| --- | --- | --- |
| Machine hôte | fichier .img | conserve les octets de l'image |
| Disque simulé | blocs physiques | contient métadonnées et contenus |
| Fichier virtuel | nom, inode, données | représente le texte demandé au menu |

Un octet contient huit bits. Un bloc rassemble un nombre fixe d'octets. Un
inode décrit un fichier et indique où lire ses données. Un répertoire relie
un nom à un numéro d'inode. Le contenu du fichier se trouve dans ses blocs.

Le format JSON des anciennes versions reste lisible. Les nouvelles créations
utilisent le binaire ; une ancienne image garde son format lors d'une écriture.

## Lire la structure du disque

L'image binaire possède des zones distinctes, chacune alignée sur une frontière
de bloc. Les métadonnées précèdent les blocs réservés aux données des fichiers.

| Symbole | Zone | Informations enregistrées |
| --- | --- | --- |
| S | Superbloc | signature ESINOSB1, version, géométrie et contrôle CRC32 |
| B | Bitmap | un bit par bloc de données, libre ou occupé |
| I | Table d'inodes | taille du fichier et pointeurs directs vers ses blocs |
| R | Répertoire | nom ASCII de 1 à 64 caractères et numéro d'inode |
| # ou . | Données | bloc occupé ou libre |

La signature identifie le format. La version précise comment lire ses champs.
Les nombres sont codés en octets dans un ordre fixé par le codec. Le CRC32
permet de détecter une modification accidentelle ; il ne chiffre pas le contenu.

À l'ouverture, le programme vérifie aussi la longueur de l'image, les zones,
le bitmap, les références des inodes et les noms. Une image incohérente est
refusée plutôt qu'interprétée comme un disque vide.

## Blocs logiques et blocs physiques

Le nombre de blocs donné à initialiser désigne la capacité de DONNÉES. Les
métadonnées occupent des blocs physiques supplémentaires avant cette zone.

Le bloc logique 0 est le premier bloc disponible pour un fichier. Son numéro
physique vaut data_start, calculé par geometrie. Pour le bloc logique k :

~~~text
bloc_physique = data_start + k
position_en_octets = bloc_physique × taille_bloc
~~~

La carte affiche les zones physiques et les blocs de données. Le suivi d'un
fichier relie son nom, son inode, ses blocs logiques et leur emplacement physique.

Dans la démo, il existe 12 blocs de données de 16 octets et 4 inodes. Le texte
Bonjour depuis le disque virtuel ESINOS. mesure 40 octets et prend les blocs
logiques 0, 1 et 2 : ils contiennent 16, 16 et 8 octets utiles.

Les octets inutilisés du dernier bloc sont complétés par des zéros. La taille
inscrite dans l'inode permet de distinguer cette réserve du véritable contenu,
même quand le contenu comporte lui-même un octet nul.

## Du nom au contenu d'un fichier

Sur le disque binaire, le répertoire associe notes.txt à l'inode 1. L'inode
garde la taille et les pointeurs. Le modèle en mémoire les réunit dans un
petit dictionnaire pour rendre les fonctions Python plus faciles à suivre.

~~~text
notes.txt -> répertoire -> inode 1 -> blocs logiques 0, 1, 2
~~~

La création cherche le premier inode libre et les premiers blocs de données
libres. La lecture suit les pointeurs dans l'ordre, assemble les octets utiles,
puis décode l'ensemble en UTF-8. Ainsi, une lettre accentuée peut être partagée
entre deux blocs sans être perdue.

La suppression libère les blocs et l'inode. Un fichier vide utilise un inode
sans prendre de bloc de données. Une table d'inodes pleine et une zone de
données pleine sont donc deux limites différentes.

Les pointeurs directs sont dimensionnés au nombre de blocs de données choisi.
Cela permet à un fichier de prendre toute cette capacité. Ce choix pédagogique
augmente la place des métadonnées : le programme affiche ce coût dans la
structure physique, au lieu de le compter parmi les données utilisateur.

## Sauvegarder et migrer sans écrasement

Après une modification, ESINOS prépare toute l'image dans un fichier temporaire,
synchronise ses octets, puis remplace l'ancienne image. Si la publication échoue,
l'image précédemment publiée reste disponible. La création d'un nouveau disque
est exclusive : deux créations concurrentes sur le même chemin ont un seul gagnant.

Les anciennes images JSON conservent leur format. La migration copie leur état
validé dans un nouveau fichier binaire, sans modifier le JSON original.

~~~bash
python3 -m esinos fs --disk data/ancien.disk.json \
  migrate data/nouveau.disk.img
~~~

Le chemin de destination doit être libre. Le menu disque propose la même
copie à l'option 10. L'option 7 Reformater efface les fichiers virtuels après
confirmation. Répondre non annule l'opération.

Le disque est prévu pour une seule session de modification à la fois.
L'écriture atomique protège la publication d'une image ; elle ne fusionne
pas les modifications de deux utilisateurs travaillant simultanément.

## Exercice corrigé sur les données

Pars d'une image neuve avec 4 blocs de données de 8 octets et 2 inodes. Les
métadonnées sont réservées séparément. Crée a.txt avec 17 octets, puis b.txt
avec 4 octets. Essaie c.txt avec 9 octets. Supprime a.txt et réessaie c.txt.

### Prévoir la réponse

1. Combien de blocs de données chaque fichier demande-t-il ?
2. Pourquoi le premier essai de c.txt échoue-t-il ?
3. Quels blocs logiques reçoit c.txt après la suppression ?

### Correction

a.txt demande trois blocs et b.txt un bloc. Le premier essai de c.txt est
refusé car les deux inodes sont déjà pris. Après la suppression de a.txt,
c.txt demande deux blocs et réutilise les premières cases disponibles.

| Moment | Inode 1 | Inode 2 |
| --- | --- | --- |
| Deux créations | a.txt dans 0, 1, 2 | b.txt dans 3 |
| Suppression de a.txt | libre | b.txt dans 3 |
| Second essai | c.txt dans 0, 1 | b.txt dans 3 |

Un nom déjà utilisé est refusé. Un fichier absent ne peut pas être lu ni
supprimé. Les zones de métadonnées restent réservées après toutes ces opérations.

