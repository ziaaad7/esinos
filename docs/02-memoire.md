# Mémoire virtuelle, TLB et les deux EAT

## Remplacement de pages

Une page est une partie de l’espace logique. Un cadre est une place de même
taille dans la mémoire simulée. Lorsqu’une page demandée est déjà dans les
cadres, c’est un hit. Sinon, c’est un défaut de page. S’il ne reste aucun cadre
libre, une politique choisit une victime.

~~~text
remplacer(pages, nombre_cadres, algorithme)
    -> (nombre_defauts, trace)
~~~

La trace contient une étape par référence :

~~~text
(page, hit, victime, cadres_apres)
~~~

La victime vaut None lorsque le défaut utilise encore un cadre libre. Les trois
algorithmes acceptés sont fifo, lru et optimal.

- FIFO sort le cadre chargé depuis le plus longtemps.
- LRU sort la page utilisée le moins récemment.
- Optimal sort la page dont la prochaine utilisation est la plus lointaine,
  ou qui ne revient jamais. Il sert de référence théorique car il connaît la
  suite future.

Avec les références 7,0,1,2,0,3,0,4,2,3,0,3,2 et trois cadres, les défauts sont
10 pour FIFO, 9 pour LRU et 7 pour Optimal.

## Sous-menu remplacement

| Choix | Action |
| --- | --- |
| 1 à 3 | FIFO, LRU, Optimal |
| 4 | Comparer les trois algorithmes |
| 5 | Modifier références et cadres |
| 6 | Restaurer l’exemple |
| 0 | Retour |

Le mode Expliqué part de la trace retournée par le calcul. Il montre l’état
avant et après. Sur un hit, il précise que FIFO ne change pas l’ordre et que
LRU rafraîchit la page. Pour Optimal, il explique le futur et les égalités sont
départagées par le plus petit numéro de cadre.

~~~bash
python3 -m esinos memory --algorithm fifo --frames 3 \
  --references "7,0,1,2,0,3,0,4,2,3,0,3,2" --explain
~~~

## Traduire une adresse

Une adresse logique se sépare par division entière et modulo.

~~~text
page = adresse // taille_page
déplacement = adresse % taille_page
adresse_physique = cadre * taille_page + déplacement
~~~

Le contrat est :

~~~text
traduire(adresses, taille_page, table_pages, capacite_tlb=2)
    -> (lignes, hits)
~~~

Chaque ligne est :

~~~text
(adresse, page, déplacement, cadre, adresse_physique, hit_tlb)
~~~

La table associe une page à un cadre. Le cadre 0 est valide. Si la page est
absente de la table, le cadre et l’adresse physique sont None. Cet accès est un
miss du point de vue du taux TLB.

Le TLB garde les traductions récentes avec LRU. Une capacité de 0 désactive le
cache sans empêcher la traduction par la table des pages.

~~~bash
python3 -m esinos translate --page-size 64 --page-table "0:5,1:2,2:7,3:1" \
  --addresses "5,70,75,130,5,195,70,260" --tlb-size 2 --explain
~~~

Dans cet exemple, l’adresse 75 est traduite en 139 et réutilise l’entrée de la
page 1. La page 4 demandée par 260 est absente. Le résultat est 1 hit sur 8.

Le sous-menu traduction permet de lancer le scénario, modifier adresses, taille,
table, capacité et temps, puis restaurer l’exemple. Les explications montrent
quotient, reste, TLB avant et après, hit ou miss et éviction LRU.

## EAT TLB

Le premier modèle mesure seulement le coût de la recherche de traduction et des
accès mémoire. Il ne facture pas le chargement depuis le disque.

~~~text
calculer_eat(hits, acces, temps_tlb=10, temps_memoire=100)
EAT = temps_tlb + (2 - taux_hit) * temps_memoire
~~~

Un hit coûte temps_tlb + temps_memoire. Un miss coûte temps_tlb +
2 * temps_memoire, car la table puis la donnée sont consultées. Avec 1 hit sur
8, 10 ns de TLB et 100 ns de mémoire, l’EAT est 197.50 ns.

## EAT avec défauts de page

Le second modèle est distinct. Il utilise un taux de défaut et le temps total
du traitement complet d’un défaut.

~~~text
calculer_eat_defauts(
    taux_defaut,
    temps_memoire=100,
    temps_defaut=1000000
)
EAT = (1 - taux_defaut) * temps_memoire
      + taux_defaut * temps_defaut
~~~

temps_defaut est déjà le traitement total du défaut. Il ne faut pas lui ajouter
temps_memoire une seconde fois. Le taux doit être fini et compris entre 0 et 1.
Les deux temps doivent être finis et positifs ou nuls.

Le choix 6 du menu principal ouvre ce calcul. La même opération est disponible
dans le Terminal.

~~~bash
python3 -m esinos eat --fault-rate 0.001 --memory-time 100 \
  --fault-time 1000000
~~~

Le calcul est :

~~~text
0,999 × 100 + 0,001 × 1 000 000 = 1099,90 ns
~~~

Ce modèle ne remplace pas l’EAT TLB. Les deux répondent à des questions
différentes et sont affichés séparément.

