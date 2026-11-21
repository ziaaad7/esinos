# Mémoire virtuelle

Les choix 2, 3 et 6 du menu principal traitent respectivement le remplacement
de pages, la traduction d'adresses et l'EAT avec défauts.

## Remplacement de pages

Le sous-menu 2 propose FIFO, LRU, Optimal et leur comparaison. Le choix 5
change les pages et le nombre de cadres ; le choix 6 restaure l'exemple.

- FIFO retire la page chargée la première.
- LRU retire la page utilisée le moins récemment.
- Optimal retire la page dont la prochaine utilisation est la plus lointaine.
  Il suppose que le futur est connu et sert de référence théorique.

Chaque accès montre le hit ou défaut, la victime éventuelle et l'état des
cadres. Sur 7,0,1,2,0,3,0,4,2,3,0,3,2 avec trois cadres, les défauts valent
10, 9 et 7. Les guides d'apprentissage détaillent la raison des évictions.

## Traduction et TLB

Dans le sous-menu 3, le choix 1 lance l'exemple et le choix 2 modifie ses
paramètres : adresses, taille de page, table, capacité du TLB et temps d'accès.

```text
page = adresse // taille_page
déplacement = adresse % taille_page
adresse physique = cadre × taille_page + déplacement
```

Le TLB garde les traductions récentes et utilise LRU. Une capacité de 0
désactive ce cache. Le cadre 0 est valide. Une page non représentée dans la
table est signalée comme absente dans ce modèle ; son adresse physique vaut None.

Avec une taille de page de 64 et la page 1 dans le cadre 2, l'adresse 70 donne
134. L'adresse 75 donne 139 et réutilise la traduction, donc produit un hit.
La démonstration complète obtient 1 hit sur 8 accès.

## Deux modèles d'EAT

Le modèle TLB exclut le délai de chargement d'une page et utilise le taux h :

```text
EAT_TLB = temps_TLB + (2 - h) × temps_mémoire
```

Avec 10 ns de TLB, 100 ns de mémoire et h=1/8, il donne 197,50 ns.
Un accès à une page absente compte comme un miss dans cette expérience.

Le choix 6 du menu principal étudie séparément le taux de défaut p :

```text
EAT_défauts = (1 - p) × temps_mémoire + p × temps_défaut
```

temps_défaut est le coût TOTAL du traitement d'un accès avec défaut. Pour
p=0,001, mémoire=100 ns et défaut=1 000 000 ns, le résultat est 1 099,90 ns.
Ces deux modèles ne sont pas additionnés automatiquement. Les temps non finis
ou négatifs et les taux hors de 0 à 1 sont refusés.

memory.py effectue les calculs et les tableaux affichent leurs traces.
