# Plan

Ce qui reste à faire. Une tâche finie est retirée de la liste dans la PR qui la
termine ; l'histoire reste dans git.

## Avant le prochain scrutin

- [ ] **Raccourcir le délai jusqu'au visiteur** : aujourd'hui environ 2 min,
      jusqu'à 6, et souvent deux rechargements. Par ordre de gain :
      - rafraîchir le cache nginx à la fin de chaque tour (`proxy_cache_bypass`
        accepté de la machine seule) : plus de version périmée servie au
        premier visiteur, plus de rendu à froid ;
      - import en un seul `executemany`, lignes estimées dans une seule
        transaction ;
      - une boucle qui reste en vie et interroge le fichier fédéral toutes les
        30 s, en sautant les tours où il n'a pas changé ;
      - moindres carrés en forme close au lieu de `minimize`, après
        vérification sur tout le backtest.
- [ ] **Page des erreurs de saisie communales**, publique, mise à jour à
      chaque tour (méthode : [`doc/anomalies.md`](doc/anomalies.md)). La
      machine calcule et classe ; le contexte reste le travail d'un humain ou
      d'un agent, avec une note libre par commune.
      - **Rouge**, faute probable : une correction simple (oui/non inversés,
        objets intervertis, chiffre mal saisi) explique l'écart (Verzasca,
        Wolfhalden, Büttenhardt, Ursins).
      - **Orange**, à regarder : écart fort ou bulletins incohérents, sans
        correction qui explique tout (Saint-Saphorin, Marchissy).
      - **Vert** : le reste, masqué par défaut.
      - Liste triée par gravité ; au clic, quatre graphiques : observé contre
        prédit pour tout l'objet (avec la position corrigée), bulletins par
        objet, mini-carte des voisines, écarts de la commune aux scrutins
        passés.
      - Les communes rouges restent dans l'ajustement.

## Modèle

Les chiffres et les impasses sont dans [`doc/backtest.md`](doc/backtest.md).
Chaque étape change les valeurs projetées : une à la fois, et jamais dans la
semaine d'un scrutin.

- [ ] **Pondérer l'ACP par la taille des communes**, dans `populate_pca`
      seulement. Erreur médiane 0,445 → 0,366 point : à faire en premier.
- [ ] **Nombre de composantes** : ~20 au lieu de 6, croissant avec le
      dépouillement. Le garde-fou de `get_extrapolation` (7 communes) doit
      suivre le nombre de paramètres.
- [ ] **Fourchette calibrée** sur le backtest, en fonction de l'avance, pour
      remplacer le ±2,5 points en dur.
- [ ] **Réfléchir à comment gérer les résultats partiels** des grandes
      communes (voir [`doc/depouillement.md`](doc/depouillement.md)).

## Produit

- [ ] Bouton pour montrer ou masquer les communes estimées sur les cartes :
      masquées, elles passent au gris des communes en attente.
- [ ] Bloc « Au fil de la journée », un panneau de plus à côté des objets :
      tous les objets du jour sur un même graphique, projection et fourchette
      au fil de l'heure, dépouillé en discret ; échelle de 20 à 80 % avec la
      ligne des 50 %, fond qui dit le verdict, couleur et nom au bout de
      chaque courbe. Demande l'historique des projections dans le contrat de
      vue.
- [ ] `404.html` dans la charte du site, et un favicon.

## Ménage

- [ ] `ruff format` sur tout le dépôt, dans une PR à part.
- [ ] `ScrutinAPI.get_nb_inscrit` n'a plus d'appelant : la supprimer
      avec son test.
- [ ] Trier les branches distantes : la plupart sont fusionnées ou
      abandonnées.
