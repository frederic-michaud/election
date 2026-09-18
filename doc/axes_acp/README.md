# Analyse des axes de l'ACP : notes internes

Ce document est le **document 2**, destiné aux administrateurs du site et aux agents qui
reprendront l'analyse. Le **document 1** est [`doc/axes_acp.pdf`](../axes_acp.pdf) : il est
public, sans jargon technique, et on peut le partager sur le site.

- **État au 18.09.2026.** Branche `moteur/analyse-axes-acp`, partie de `master` (1f4c8ec),
  poussée **sans PR**. Rien n'est prévu pour `master` pour l'instant : on décidera plus tard
  s'il faut en faire une page du site.
- **Question de départ.** Que mesurent les six axes de l'ACP ? La demande portait sur une lecture
  du type « nationaliste contre ouverture », « droite économique contre État fort ». Elle voulait
  aussi :
  - la documentation de chaque objet (enjeu, qui soutenait quoi) ;
  - plusieurs façons de nommer les axes ;
  - une classification des objets.

---

## Démarrage rapide (pour un agent)

```bash
# depuis la racine du dépôt, venv avec requirements/calcul.txt
pip install -r doc/axes_acp/requirements.txt       # matplotlib, typst
python doc/axes_acp/analyse.py --telecharger \
    --base var/reel-veille.sqlite3 \
    --base-avant var/juin-1815.sqlite3 \
    --contours <clone>/carte/static/carte           # voir « Pièges »
python doc/axes_acp/construire.py                   # → doc/axes_acp.pdf
```

- **Pour modifier seulement le texte**, il suffit de lancer `construire.py`, qui compile en
  1 à 2 secondes. `resultats.json` et `figures/` sont committés précisément pour cela : on
  peut réécrire le document sans la base réelle, qui n'est pas dans git.
- **Pour recalculer les données**, `analyse.py` prend une quinzaine de secondes : ACP, rotations,
  variantes et figures.
- **Premier contrôle après tout recalcul :** `meta.reproduction` dans `resultats.json` doit
  valoir 1 sur les six axes, avec `meta.ecart_max` égal à 0. Cela prouve qu'on interprète
  bien l'ACP de `populate_pca`, qui fait foi : rien ici n'écrit dans la base.

---

## Fichiers

| Fichier | Rôle | À la main ? |
|---|---|---|
| `analyse.py` | Tout le calcul, sans Django : lit SQLite en lecture seule (`mode=ro`), écrit `resultats.json` et `figures/` | code |
| `construire.py` | Compile `axes_acp.typ` avec le paquet Python `typst` et écrit `doc/axes_acp.pdf` | code |
| `axes_acp.typ` | Mise en page **et texte** du document public. Les tableaux lisent `resultats.json` ; la prose est rédigée | **oui** |
| `fiches.typ` | Commentaire des 32 fiches de l'annexe A (dictionnaire `numéro OFS de l'objet → texte`) | **oui** |
| `objets.csv` | Une ligne par objet : `sujet_id\|titre\|etiquette\|theme\|enjeu`. **Séparateur `\|`**, car les enjeux contiennent des « ; » | **oui** |
| `resultats.json` | Sortie de `analyse.py`, committée (≈ 320 Ko) | généré |
| `figures/` | Plans et cercles en PDF vectoriel ; cartes en PNG à 300 dpi (≈ 3 Mo), committées | généré |
| `requirements.txt` | Dépendances en plus de `requirements/calcul.txt` | — |

Sources mises en cache hors de git, dans `var/sources/` :
- `swissvotes_dataset.csv` (2,7 Mo) ;
- `nr_meta.json` ;
- `nr2023_force_partis_communes.json` et `nr2019_force_partis_communes.json`.

`--telecharger` les recrée.

### Structure de `resultats.json`

- `meta` : effectifs, dates, contrôle de reproduction.
- `variance` : les 10 premiers axes.
- `angle_rotation` : l'angle de la rotation varimax des axes 1 et 2, en degrés.
- `axes[k]`, un par axe :
  - `variance`, `ecart_type` ;
  - `objets_bas` et `objets_haut` (numéros d'objet) ;
  - `communes` (extrêmes) ;
  - moyennes par `langue`, `urbanisation` et `canton`.
- `facteurs[k]` : même forme, pour F1 à F3 (rotation varimax sur trois axes), plus
  `congruence_axes`.
- `acteurs[cle]` :
  - `alignement` : corrélation entre ses mots d'ordre et la corrélation des objets avec l'axe ;
  - `position` : l'acteur projeté comme une commune fictive ;
  - `position_rot` : la même projection, sur les facteurs tournés.
- `r2_objets`, `r2_objets_rot` : R² des modèles « mots d'ordre → corrélation objet–axe ».
- `r2_communes`, `r2_communes_rot` : R² des modèles « langue, urbanisation, partis → position
  des communes ».
- `motifs` : les configurations de mots d'ordre.
- `suivi` : indices de suivi par acteur.
- `force_partis` : corrélations avec la force des partis en 2023.
- `villes` : la position de quelques villes.
- `robustesse` : `ponderee`, `reduite`, `periodes`, `varimax6`, `ajout`.
- `objets[i]`, un par objet :
  - textes de `objets.csv` ;
  - données Swissvotes (type, auteur, `paroles`, `dissidences`) ;
  - géographie (`groupes`, `cantons_extremes`) ;
  - `axes`, `facteurs`, `dimension` (famille), `qualite` (Σ corr² sur 6 axes).
- `futurs` : prédiction pour les objets du 27.09.2026.

---

## Versions utilisées (18.09.2026, macOS 13)

| Outil | Version |
|---|---|
| Python | 3.14.5 |
| numpy / pandas / scipy | 2.5.3 / 2.3.3 / 1.18.1 |
| scikit-learn | 1.9.1 (`PCA(n_components=6)`, la même classe que `populate_pca`) |
| matplotlib | 3.11.2 (backend Agg, qui mesure les textes pour placer les étiquettes ; sortie PDF et PNG) |
| typst (paquet PyPI) | 0.15.0 (il embarque le compilateur, sans installation système) |
| pypdf | 6.19.0 (seulement pour lire le codebook Swissvotes ; pas nécessaire au calcul) |
| Polices | Helvetica Neue (macOS) dans les figures et le PDF, avec repli sur Helvetica, Arial, DejaVu Sans. Sous Linux, la mise en page changera légèrement |

Sources, avec leur empreinte (les 16 premiers caractères du sha256) :
- `swissvotes_dataset.csv` : 714 lignes × 874 colonnes, `5c32d0d6e61e9ce9`, téléchargé le
  18.09.2026 à 15:57 ;
- `nr2023_force_partis_communes.json` : `7d0e1f038ca3918e`.

---

## Méthode, dans le détail

1. **Matrice.** C'est la même que `ScrutinAPI.getVotationMatrixWithMetaInfo`, relue en SQL :
   - chaque case vaut `nombre_oui / (nombre_oui + nombre_non)` ;
   - on garde les communes qui ont tous les objets, soit 2 115 : 2 103 communes et 12
     pseudo-communes de Suisses de l'étranger, numérotées 9xxx.

   On obtient 103 objets, du 30.11.2014 au 14.06.2026.
2. **ACP du site.** `sklearn.decomposition.PCA(6)`, centrée, non réduite, non pondérée. La
   lecture des axes passe par la corrélation objet–axe, celle du cercle de `/objets-acp`. On
   garde les signes du site, que sklearn fixe de façon déterministe.
3. **Acteurs projetés.** Chaque mot d'ordre devient une commune fictive : oui → 1, non → 0,
   liberté de vote → 0,5, inconnu → moyenne de la colonne, ce qui ne pèse sur rien. On la
   passe ensuite par `modele.transform`. L'**alignement** est la corrélation, sur les objets
   où l'acteur a dit oui ou non, entre son mot d'ordre (±1) et la corrélation objet–axe.
4. **R² objets.** On régresse, par moindres carrés, la corrélation objet–axe sur les mots
   d'ordre (±1, 0 si inconnu), sur une indicatrice « initiative » et sur les indicatrices du
   domaine politique Swissvotes de premier niveau (`d1e1`).
5. **Communes.**
   - L'**indice de suivi** d'un acteur est la part moyenne des votants qui ont voté comme il
     le recommandait (objets à ±1).
   - La force des partis 2023 vient du cube OFS px-x-1702020000_105. Le Centre y est la
     somme Centre + PDC + PBD. La gauche est PS + Verts + PST + Sol. La droite nationale est
     UDC + UDF + Lega + MCR. Il manque 6 communes, issues de fusions postérieures à 2023.
6. **Rotation.**
   - Varimax (Kaiser, γ = 1) sur la matrice des corrélations objet–axe des k premiers axes
     (k = 2, 3, 6).
   - Orientation : le PS du côté positif de F1, le PLR de F2, les Verts de F3.
   - Scores tournés = (scores / écart-type) @ R.
   - Part de variance d'un facteur = Σ charges² du facteur / Σ charges² des trois axes ×
     variance des trois axes.
7. **Classification.** La famille d'un objet est l'argmax des charges² de la rotation à trois
   facteurs. La **qualité** d'un objet est Σ corr² sur les six axes.
8. **Robustesse.**
   - Pondérée : variante B1 de `PLAN_AMELIORATION_MODELE.md`, SVD de `√w·(X − μ_w)` avec
     `w = nb_voix`. On compare par la congruence de Tucker des vecteurs propres.
   - Réduite : ACP sur les objets standardisés.
   - Périodes : ACP sur 2014-2019 (42 objets) et sur 2020-2026 (61 objets).
   - Ajout d'un scrutin : comparaison avec `var/juin-1815.sqlite3`, qui n'a pas le 14.06.2026.

   Pour ces trois dernières variantes, on compare la corrélation absolue des scores des
   communes.
9. **Mots d'ordre Swissvotes.**
   - Codes : `1` → +1, `2` → −1, `3/4/5` → 0 ; `9999` ou `.` → absent.
   - Question subsidiaire (`rechtsform = 5`) : `9` (préférer l'initiative) → +1, `8` → −1.
     C'est cohérent avec l'OFS, qui compte comme « oui » la préférence pour l'initiative.
   - Centre : `p-mitte`, puis `p-cvp` avant 2021.
   - Dissidences : `pdev-<parti>_<canton>`.
   - Appariement : `vorlagenId = 10 × anr`. Les 103 objets s'apparient, avec des dates
     identiques et un % de oui à 0,09 point près.
10. **Prédiction d'un objet futur.** Régression, sur les 103 objets, des corrélations avec
    les axes 1 à 3 et les facteurs F1 à F3, sur les mots d'ordre du Conseil fédéral et des
    six grands partis. Les voisins sont ceux dont les mots d'ordre sont les plus proches
    (distance L1), un domaine différent comptant pour 2.

---

## Valeurs de référence au 18.09.2026 (pour détecter un changement)

- **Variance des axes 1 à 10 (%) :** 47,94 · 14,40 · 9,34 · 3,30 · 3,17 · 2,31 · 1,45 ·
  1,33 · 0,87 · 0,79.
- **Rotation :** 38,5°. Parts de F1, F2, F3 : 31,2 %, 28,3 %, 12,2 %. F3 a une congruence de
  1,00 avec l'axe 3.
- **Indices de suivi :**
  - axe 1 : PS +0,97, UDC −0,95 ;
  - axe 2 : PLR −0,85 ;
  - F2 : PVL +0,98.
- **Signes du site :**
  - axe 1 positif = gauche ;
  - axe 2 positif = contestation (argent liquide +0,79) ;
  - axe 3 positif = écologie (forfaits fiscaux +0,76) ;
  - axe 4 positif = catholique (frein aux coûts +0,59) ;
  - axe 5 positif = Grisons (loi sur la chasse +0,39).

  Si un recalcul inverse l'un de ces signes, les libellés et la prose sont faux.
- **Robustesse** (axes 1 à 6, variante / site) :

  | Variante | Axe 1 | Axe 2 | Axe 3 | Axe 4 | Axe 5 | Axe 6 |
  |---|---|---|---|---|---|---|
  | Pondérée (B1) | 0,94 | 0,82 | 0,76 | 0,54 | 0,57 | 0,89 |
  | Réduite | 0,99 | 0,94 | 0,93 | 0,65 | 0,57 | 0,88 |
  | 2014-2019 | 0,98 | 0,75 | 0,73 | 0,74 | 0,70 | 0,11 |
  | 2020-2026 | 0,99 | 0,98 | 0,97 | 0,78 | 0,76 | 0,92 |
  | Sans le 14.06 | 1,00 | 1,00 | 1,00 | 1,00 | 1,00 | 1,00 |

---

## Décisions ouvertes (pour les administrateurs)

1. **Publier le document 1 ? Où, sous quelle forme ?**
   - Deux possibilités : un PDF lié depuis une page du menu (`page_statique`), ou une page
     HTML dédiée.
   - Le PDF est prêt. Une page HTML demanderait de réécrire la mise en page avec la charte,
     ce qui relève de la voie I.
   - À faire de préférence **après le 27.09.2026**, pour que la dernière votation y figure.
2. **Nommer les axes sur les pages ACP ?** Le document 1 propose des libellés courts. Le
   risque : `populate_pca` peut inverser un signe ou échanger deux axes proches (4 ↔ 5) au
   prochain recalcul.
   - Option A : ne rien afficher. C'est la situation actuelle.
   - Option B : des libellés en dur, relus à chaque scrutin. C'est fragile, et contraire à la
     préférence pour ce qui reste juste sans retouche quand l'ACP change.
   - Option C (recommandée) : `populate_pca` oriente chaque axe sur un repère fixe, par
     exemple l'indice de suivi du PS positif sur l'axe 1 et celui du Conseil fédéral négatif
     sur l'axe 2. Il conserve les vecteurs de référence et signale toute congruence < 0,9 ou
     tout changement de rang. Les libellés restent alors justes sans retouche, et l'on sait
     quand ils cessent de l'être. C'est une tâche de la voie M, à étiqueter [2] dans le plan.
3. **Montrer le plan tourné (F1 gauche–droite × F2 ouverture–souverainisme) sur
   `/nuage-acp` ?** Il est plus parlant que le plan 1 × 2. Il faudrait :
   - que la voie M ajoute la matrice de rotation au contrat de `pca/donnees.py` ;
   - que la voie I ajoute un sélecteur de plan.

   La rotation se recalcule à chaque ACP ; avec l'orientation de l'option C, elle reste stable.
4. **Interaction avec `PLAN_AMELIORATION_MODELE.md`.**
   - Passer à 20 composantes (A1) ne change pas les six premiers axes, puisque les
     composantes d'une ACP sont emboîtées.
   - Pondérer par la taille (B1) change les axes 2 à 5 (voir le tableau de robustesse). Si
     B1 est adoptée pour les pages de lecture aussi, il faut relancer l'analyse et relire les
     libellés 2 à 5. On peut aussi garder une ACP non pondérée pour l'affichage et la
     pondérée pour l'extrapolation.

---

## À vérifier après le 27.09.2026

La section a été retirée du document public, parce qu'elle serait périmée le lendemain. Les
mots d'ordre venaient de Swissvotes, complétés par la presse (`PAROLES_COMPLEMENTAIRES` dans
`analyse.py`) :
- neutralité : Centre et Verts non ;
- alimentation : UDC non, Centre non, Verts liberté de vote.

| Objet | Axe 1 | Axe 2 | Axe 3 | F1 | F2 | F3 | Voisins par les mots d'ordre |
|---|---|---|---|---|---|---|---|
| 6880 Neutralité | −0,50 | +0,32 | +0,05 | −0,19 | −0,56 | +0,05 | limitation, renvoi, « vache à lait », No Billag, autodétermination, burqa |
| 6890 Alimentation | +0,01 | +0,31 | +0,42 | +0,20 | −0,24 | +0,42 | monnaie pleine, or, Ecopop, revenu de base, service public, souveraineté alimentaire |

Ce que la prédiction laisse attendre pour le soir du vote :
- **Neutralité.** Ses voisins sont très bien captés par les six axes : la qualité vaut 0,86 à
  0,89 pour la limitation, le renvoi et l'autodétermination, contre une médiane de 0,78. Une
  bonne projection est donc probable.
- **Alimentation.** Ses voisins par les mots d'ordre sont mal captés (monnaie pleine 0,45,
  service public 0,55). Son voisin thématique, les vaches à cornes (0,42), est aussi le pire
  cas du backtest. Il faut donc s'attendre à une projection plus incertaine.

**Contrôle à faire** une fois le 27.09 importé dans l'historique :
1. relancer l'analyse ;
2. comparer les corrélations réelles des deux objets aux valeurs du tableau ;
3. comparer l'erreur de projection de la soirée à ce pronostic.

---

## Pièges rencontrés

- **Contours.** `carte/static/carte/communes.geojson` et `lacs.geojson` sont sur
  `origin/moteur/carte-detaillee` (commit ba267d2), **pas sur `master`**. Il faut passer
  `--contours` vers un clone de cette branche tant qu'elle n'est pas fusionnée.
- **Base réelle.** Elle n'est pas dans git (`var/`). Pour la reconstruire, suivre le pipeline
  de `CLAUDE.md` avec `importer_historique --depuis 2014-11-30`. `var/juin-1815.sqlite3` est
  la même base sans le 14.06.2026 ; elle est facultative : sans elle, la ligne de stabilité
  disparaît du tableau.
- **Résultats cantonaux récents.** Swissvotes n'a pas encore les colonnes `xx-japroz` pour les
  objets votés depuis juin 2024. `analyse.py` recalcule donc les résultats cantonaux depuis les
  communes, Suisses de l'étranger compris. L'écart avec Swissvotes, là où il existe, est au
  plus de 0,15 point. Les totaux `kt-ja` et `kt-nein` restent ceux de Swissvotes.
- **Polices.** Helvetica Neue n'a ni flèches (← →) ni triangles (◀ ▶) : il faut les éviter
  dans les figures, matplotlib ne ferait qu'avertir.
- **Cartes.** En PDF vectoriel, elles pèsent 2,3 Mo chacune ; d'où le PNG à 300 dpi.
- **Étiquettes des nuages.** `_etiqueter` mesure les textes avec le rendu Agg et les écarte
  verticalement. `_colonnes` range les étiquettes des cercles en deux colonnes. Il faut fixer
  les limites des axes **avant** de les appeler.
- **Typst.** `#columns` ne répartit pas le contenu entre colonnes : les listes de familles
  passent par un `grid` à trois colonnes découpé à la main. Les tableaux héritent d'un
  alignement par défaut, avec la première colonne à gauche et les suivantes à droite.
- **Code couleur.** Rouge et bleu viennent de `scrutin/charte.py` : bleu pour le côté positif,
  rouge pour le côté négatif, le même code que l'accueil. Une palette propre à chaque axe a déjà été
  essayée puis rejetée. Les
  catégories (langues, familles) utilisent les trois premiers créneaux de la palette dataviz
  validée : `#2a78d6`, `#eb6834`, `#1baf7a`.

---

## Compléter l'analyse

### Après un nouveau scrutin

1. Mettre à jour la base (`importer_historique`, `set_nb_voix_commune`, `populate_pca`).
2. Ajouter une ligne par objet à `objets.csv`. Sinon, `analyse.py` s'arrête et liste les
   objets qui manquent.
3. Lancer `analyse.py` et vérifier `meta.reproduction`. Comparer ensuite aux **valeurs de
   référence** ci-dessus : signes, parts de variance, congruence des facteurs.
4. Si les axes ont bougé, relire la **prose écrite à la main**, qui ne se met pas à jour
   toute seule :
   - dans `axes_acp.typ` :
     - la liste « En bref » et le tableau des libellés ;
     - les paragraphes « Ce qui est en jeu » et « Où » du § 3, ainsi que les noms de
       communes et de cantons cités dans les §§ 3 et 4 ;
     - les quadrants ;
     - le tableau des grilles de lecture du § 5 ;
     - le commentaire de la classification ;
   - tous les chiffres de `fiches.typ`.
5. Lancer `construire.py`, puis relire le PDF page par page. Typst peut produire des PNG par
   page avec `typst.compile(..., format="png")` : c'est la méthode utilisée ici pour la
   relecture.

### Pistes non explorées

- **Covariables socio-démographiques de l'OFS** (portraits des communes : revenu, part
  d'étrangers, confession, formation). Elles permettraient de tester trois hypothèses du
  document :
  - le niveau de vie sur F1 ;
  - le caractère confessionnel de l'axe 4, par la part de catholiques ;
  - le profil urbain et diplômé de F3, affirmation retirée faute de données.
- **Sondages VOTO** : valider au niveau individuel ce qui n'est ici mesuré que par commune.
- **Axes 7 et suivants**, si `populate_pca` passe à 20 composantes (plan A1).
- **Refaire le document en pondérant par la taille**, si B1 est adoptée.
- **Page web interactive** : un nuage Plotly du plan tourné et le tableau filtrable des 103
  objets, si l'on choisit la forme HTML (décision 1).

---

## Sources

- Swissvotes, jeu de données et codebook :
  <https://swissvotes.ch/page/dataset/swissvotes_dataset.csv>,
  <https://swissvotes.ch/page/dataset/codebook-de.pdf>.
- OFS STAT-TAB, API PX-Web sans clé :
  - `px-x-1703030000_101` (votations par commune, via `importer_historique`) ;
  - `px-x-1702020000_105` (Conseil national, force des partis par commune).
- Hermann et Leuthold (2003), *Atlas der politischen Landschaften*, vdf. Leurs trois
  dimensions (links–rechts, liberal–konservativ, ökologisch–technokratisch) ont été vérifiées
  à partir d'un compte rendu de Perlentaucher.
- Kriesi et al. (2008), *West European Politics in the Age of Globalization*, CUP.
- Mots d'ordre du 27.09.2026 : RTS, « Votation : tous les partis sauf l'UDC rejettent
  l'initiative » ; Verts : liberté de vote sur l'alimentation (presse, septembre 2026).
- Loi sur le service civil du 14.06.2026 (mesures) : ch.ch, easyvote, 20 minutes.
