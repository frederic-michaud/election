# Plan

Ce qui reste à faire. **[M]** voie Moteur, **[I]** voie Interface, **[2]** à
décider à deux. Une tâche finie est retirée de la liste dans la PR qui la
termine ; l'histoire reste dans git.

## Avant le prochain scrutin

- [ ] **[M]** Sauvegarde quotidienne de la base : copie datée par
      `VACUUM INTO` (sûr à chaud), déclenchée par un timer. L'historique
      `ResultatCommunalHistorique` est le bien précieux du projet.
- [ ] **[M]** Détecteur d'erreurs de saisie dans le pipeline du jour J : la
      méthode a fait ses preuves (4 sur 4, voir
      [`doc/anomalies.md`](doc/anomalies.md)) mais vit encore hors du dépôt.
- [ ] **[M]** Mesurer chaque étape d'un tour de la boucle (téléchargement,
      démarrage des conteneurs, import, extrapolation, rendu), puis rapprocher
      et optimiser ce qui domine.

## Modèle [M]

Les chiffres et les impasses sont dans [`doc/backtest.md`](doc/backtest.md).
Chaque étape change les valeurs projetées : une à la fois, et jamais dans la
semaine d'un scrutin.

- [ ] **Pondérer l'ACP par la taille des communes** : centrage pondéré puis
      SVD de `√w·(X − μ_w)`, dans `populate_pca` seulement. Erreur médiane
      0,445 → 0,366 point. Le meilleur rapport gain/risque : à faire en premier.
- [ ] **Nombre de composantes** : ~20 au lieu de 6 (0,445 → 0,337 ; six pires
      1,385 → 0,749), croissant avec le dépouillement plutôt que fixe. Le
      garde-fou de `get_extrapolation` (7 communes) doit suivre le nombre de
      paramètres effectif.
- [ ] **Taille de la commune comme régresseur** (`log₁₀` des électeurs) :
      règle la queue (six pires 1,385 → 0,784) mais dégrade les faibles avances
      et une dizaine d'objets faciles. Préalable : vérifier que le premier
      dépouillement publié est bien vers 25 % (voir
      [`doc/depouillement.md`](doc/depouillement.md)). Variante à explorer :
      une pénalité ridge sur ce seul coefficient, qui s'efface à mesure que
      l'étendue des tailles observées couvre celle du pays.
- [ ] **Fourchette calibrée** sur les trajectoires d'erreur du backtest, en
      fonction de l'avance, pour remplacer le ±2,5 points en dur
      (`MARGE_PROVISOIRE`). Modulable par objet d'un facteur 1,5 au plus.
- [ ] **Résultats partiels des villes** : les prendre comme estimation
      provisoire au-delà de ~90 % des voix, sans les compter comme dépouillés.
      Bâle serait disponible trois heures plus tôt. À évaluer sur plusieurs
      scrutins avant de fixer un seuil (voir `doc/depouillement.md`).

## Produit

- [ ] **[I]** Cartes qui distinguent réel et estimé (`comptabilise` est déjà
      dans le contrat).
- [ ] **[2]** Courbe de convergence de la soirée : les instantanés
      `Extrapolation` sont en base, il reste à les servir et à les tracer.
- [ ] **[2]** Krigeage des résidus pour les valeurs communales des cartes
      (r = 0,42 par commune ; inutile pour la projection nationale).
- [ ] **[M]** Validation rétrospective publiée : l'erreur de projection en
      fonction de l'avance, sur les votations passées.
- [ ] **[I]** `404.html`, favicon, tableau des valeurs sous les figures.
- [ ] **[2]** Élections : généraliser du oui/non au multi-candidats (modèles
      `Scrutin`/`Candidat`, méthode des reports de voix du dépôt
      `extrapolation_politique`, sources cantonales, VD d'abord).

## Ménage

- [ ] **[2]** `ruff format` sur tout le dépôt, dans une PR à part.
- [ ] **[M]** `ScrutinAPI.get_nb_inscrit` n'a plus d'appelant : la supprimer
      avec son test.
- [ ] **[2]** Trier les branches distantes : la plupart sont fusionnées ou
      abandonnées.
