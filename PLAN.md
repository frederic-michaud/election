# Plan

Ce qui reste à faire. Une tâche finie est retirée de la liste dans la PR qui la
termine ; l'histoire reste dans git.

## Modèle

Les chiffres et les impasses sont dans [`doc/backtest.md`](doc/backtest.md).
Chaque étape change les valeurs projetées : une à la fois, et jamais dans la
semaine d'un scrutin.

Rien d'ouvert pour l'instant.

## Produit

- [ ] Bloc « Au fil de la journée », un panneau de plus à côté des objets :
      tous les objets du jour sur un même graphique, projection et fourchette
      au fil de l'heure, dépouillé en discret ; échelle de 20 à 80 % avec la
      ligne des 50 %, fond qui dit le verdict, couleur et nom au bout de
      chaque courbe. Demande l'historique des projections dans le contrat de
      vue.
- [ ] **Dire au visiteur quand arrivent les prochains résultats** : heure de
      la dernière mise à jour et de la prochaine possible (le fichier fédéral
      est interrogé toutes les 15 s, importé au plus toutes les 2 min), et un
      petit bouton pour recharger les résultats. La page doit rester la même
      pour tous, donc cachable : l'heure se calcule dans le navigateur. Demande
      l'heure du dernier import dans le contrat de vue.
- [ ] `404.html` dans la charte du site, et un favicon.

## Ménage

- [ ] `ruff format` sur tout le dépôt, dans une PR à part.
- [ ] `ScrutinAPI.get_nb_inscrit` n'a plus d'appelant : la supprimer
      avec son test.
- [ ] Trier les branches distantes : la plupart sont fusionnées ou
      abandonnées.
