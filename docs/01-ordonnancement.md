# Ordonnancement CPU

Depuis le menu principal, choisis 1. Un exemple est déjà chargé.

| Choix | Action |
| --- | --- |
| 1 à 4 | FCFS, SJF, Round Robin ou Priority |
| 5 | Comparer les quatre politiques sur les mêmes processus |
| 6 | Saisir les processus un par un |
| 7 | Restaurer l'exemple |
| 0 | Revenir au menu principal |

Un processus possède un nom, son arrivée AT, sa durée CPU BT et sa priorité.
Le CT est calculé : c'est son instant de fin, pas une valeur à saisir.
Un petit numéro de priorité est plus urgent.

## Les quatre politiques

- FCFS exécute le premier processus arrivé.
- SJF choisit la plus courte durée parmi les processus prêts.
- Priority choisit la plus haute priorité parmi les processus prêts.
- Round Robin partage le CPU avec un quantum strictement positif.

FCFS, SJF et Priority sont non préemptifs : un processus commencé termine son
burst. Round Robin peut l'interrompre à la fin d'une tranche. Les nouvelles
arrivées à cette borne entrent dans la file avant sa réinsertion.
Les égalités sont départagées par arrivée puis nom.

## Lire les résultats

Le Gantt montre les tranches et les périodes IDLE sans processus prêt. Ses
cases ont une largeur fixe ; leurs bornes indiquent les durées exactes.
Le tableau donne PID, AT, BT, Prio, Fin (CT), Attente et Séjour.

```text
séjour = CT - AT
attente = séjour - BT
```

Le Gantt et le tableau rendent le résultat directement lisible. Les guides
d'apprentissage du dépôt détaillent les règles de choix et les traces.

## Exemple reproductible

| Processus | AT | BT | Priorité |
| --- | --- | --- | --- |
| P1 | 0 | 7 | 2 |
| P2 | 2 | 4 | 1 |
| P3 | 4 | 1 | 3 |
| P4 | 5 | 4 | 2 |

| Politique | Attente moyenne | Séjour moyen |
| --- | --- | --- |
| FCFS | 4,75 | 8,75 |
| SJF | 4,00 | 8,00 |
| Round Robin, quantum 2 | 5,00 | 9,00 |
| Priority | 5,50 | 9,50 |

scheduler.py effectue les calculs. Les tests les comparent aussi à un
ordonnanceur indépendant qui avance unité par unité.
