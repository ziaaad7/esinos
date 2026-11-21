# Ordonnancement CPU

## Données manipulées

Un processus est un dictionnaire simple contenant quatre valeurs.

~~~text
{
  "nom": "P1",
  "arrivee": 0,
  "duree": 7,
  "priorite": 2
}
~~~

AT signifie instant d’arrivée et BT durée CPU. Un nom doit être unique et ne
peut pas être IDLE. L’arrivée est un entier positif ou nul, la durée est un
entier strictement positif. Une priorité plus petite est plus urgente.

Le lecteur de ligne de commande accepte le format ci-dessous. La priorité peut
être omise et vaut alors 0.

~~~text
P1:0:7:2,P2:2:4:1,P3:4:1
~~~

## Contrat de calcul

La fonction principale est :

~~~text
ordonnancer(processus, algorithme, quantum=2)
    -> (gantt, lignes)
~~~

Le Gantt est une liste de triplets nom, début, fin. Une période sans processus
prêt est un triplet IDLE. Les lignes gardent l’ordre d’entrée et contiennent :

~~~text
(nom, AT, BT, priorité, Fin ou CT, attente, séjour)
~~~

Les statistiques CPU sont calculées dans scheduler.py, pas dans le menu ni
dans le code de rendu.

~~~text
séjour = CT - AT
attente = séjour - BT
~~~

## Politiques

### FCFS

First Come, First Served exécute le processus arrivé le premier. En cas
d’égalité, l’ordre est départagé par le nom. Une fois lancé, le processus finit
sa durée CPU.

### SJF

Shortest Job First choisit parmi les processus déjà prêts celui dont BT est la
plus courte. Les égalités sont départagées par arrivée puis par nom. SJF est
non préemptif dans ce projet.

### Priority

Priority choisit parmi les processus prêts la plus petite valeur de priorité.
La règle reste non préemptive. Les égalités utilisent arrivée puis nom.

### Round Robin

Round Robin utilise une file et exécute au plus un quantum. À la fin d’une
tranche, les processus arrivés exactement à cette borne sont placés dans la
file avant la réinsertion du processus interrompu. Cette convention rend le
Gantt reproductible.

## Utiliser le sous-menu CPU

Le sous-menu démarre avec quatre processus d’exemple.

| Choix | Action |
| --- | --- |
| 1 à 4 | FCFS, SJF, Round Robin, Priority |
| 5 | Comparer les quatre politiques |
| 6 | Ouvrir l’assistant de saisie |
| 7 | Restaurer l’exemple |
| 0 | Revenir au menu principal |

L’assistant de l’option 6 demande le nombre de processus, puis leur nom, AT,
BT et priorité. L’option 5 demande le quantum utilisé pour Round Robin et
affiche les quatre résultats sur le même jeu de données.

Après un calcul individuel, Résumé affiche Gantt et tableau. Expliqué produit
une phrase par tranche. Pas à pas utilise Entrée, t et 0 comme décrit dans
[00-demarrage.md](00-demarrage.md).

## Terminal

~~~bash
python3 -m esinos scheduler --algorithm rr --quantum 2 \
  --processes "P1:0:7:2,P2:2:4:1,P3:4:1:3,P4:5:4:2"

python3 -m esinos scheduler --algorithm priority \
  --processes "P1:0:3:2,P2:1:2:1" --explain
~~~

Round Robin exige --quantum. Les noms priority et priorite désignent la même
politique dans la commande.

## Exemple reproductible

Avec P1, P2, P3 et P4 de la démonstration, les moyennes obtenues sont :

| Politique | Attente moyenne | Séjour moyen |
| --- | --- | --- |
| FCFS | 4,75 | 8,75 |
| SJF | 4,00 | 8,00 |
| RR, quantum 2 | 5,00 | 9,00 |
| Priority | 5,50 | 9,50 |

Ces valeurs sont des résultats de simulation. Elles ne mesurent pas le temps
réel du processeur de la machine.

