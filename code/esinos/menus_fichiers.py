"""Parcours interactif des inodes et des blocs persistants."""
import os
from .entrees import demander_choix, lire_avec_defaut
from .filesystem import initialiser, creer_fichier, lire_fichier
from .filesystem import supprimer_fichier, reformater, migrer_json, format_disque
from .sorties import titre, afficher_fichiers, afficher_inodes, afficher_etat
from .carte_disque import carte_blocs, explication_fichier


def menu_disque(chemin):
    if not os.path.exists(chemin):
        initialiser(chemin)
    while True:
        titre("SYSTÈME DE FICHIERS À INODES")
        print("Image :", chemin)
        print("1 Créer | 2 Lire | 3 Supprimer | 4 Lister | 5 Inodes")
        print("6 État | 7 Reformater | 8 Carte des blocs | 9 Suivre un fichier")
        print("10 Copier une ancienne image JSON en binaire")
        print("0 Retour")
        choix = demander_choix("Choix", ("0", "1", "2", "3", "4", "5",
                                        "6", "7", "8", "9", "10"), "4")
        try:
            if choix == "0":
                return
            if choix == "1":
                nom = input("Nom : ").strip()
                texte = input("Texte : ")
                inode = creer_fichier(chemin, nom, texte)
                print(f"Fichier créé dans l'inode {inode['numero']}.")
                print(explication_fichier(chemin, nom))
            elif choix == "2":
                print(lire_fichier(chemin, input("Nom : ").strip()))
            elif choix == "3":
                nom = input("Nom : ").strip()
                if input("Supprimer ce fichier ? [oui/non] : ").strip().lower() == "oui":
                    supprimer_fichier(chemin, nom)
                    print("Fichier supprimé. Ses blocs et son inode sont libres.")
                else:
                    print("Action annulée.")
            elif choix == "4":
                afficher_fichiers(chemin)
            elif choix == "5":
                afficher_inodes(chemin)
            elif choix == "6":
                afficher_etat(chemin)
            elif choix == "7":
                reponse = input("Effacer tous les fichiers virtuels ? [oui/non] : ")
                if reponse.strip().lower() == "oui":
                    reformater(chemin)
                    print("Disque reformaté.")
                else:
                    print("Action annulée.")
            elif choix == "8":
                print(carte_blocs(chemin))
            elif choix == "9":
                print(explication_fichier(chemin, input("Nom : ").strip()))
            elif choix == "10":
                if format_disque(chemin) == "binaire":
                    print("Cette image utilise déjà le format binaire.")
                else:
                    propose = os.path.splitext(chemin)[0] + ".img"
                    destination = lire_avec_defaut("Nouveau chemin .img", propose)
                    migrer_json(chemin, destination)
                    chemin = destination
                    print("Copie binaire ouverte. Le JSON original est conservé.")
        except (OSError, ValueError) as erreur:
            print("Erreur :", erreur)
