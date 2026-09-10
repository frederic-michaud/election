# Maquettes de Politiques.ch

Le laboratoire de design de la voie Interface (`PLAN_MODERNISATION.md`,
Partie 7). Des pages HTML qu'on ouvre en `file://`, avec les **vraies figures
Plotly** du site embarquées en JSON — interactives et éditables, là où un PNG
figerait ce qu'on veut faire varier.

> **Ce dossier ne va pas dans `master`.** Il vit sur la branche `maquette`,
> qui n'est jamais fusionnée : c'est un chantier de conception, pas du code de
> production. Ce qui remonte dans `master`, c'est la *transposition* du design
> retenu dans les gabarits Django, réécrite à la main. Voir Partie 7 du plan.

## Avant d'ouvrir quoi que ce soit

**Les pages sont vides tant que `construire.py` n'a pas tourné.** `figures.js`
et `plotly.min.js` sont générés, donc absents d'un clone frais — sans eux la
page s'arrête à sa première ligne de script. Depuis la racine du dépôt :

```bash
python manage.py migrate             # SQLite, une fois
python manage.py peupler_demo        # base fictive, une fois
python maquette/construire.py        # écrit figures.js, copie plotly.js
xdg-open maquette/index.html         # ou double-clic
```

Si vous tombez quand même sur une page vide, elle vous le dira : un bandeau
nomme le fichier manquant et la commande à lancer (`verifier.js`). Le sommaire
affiche de son côté la date de la dernière construction.

## Les cinq propositions

| | Variante | Parti pris |
|---|---|---|
| **A** | La une | Un objet domine, comme un quotidien. Serif de titrage, filets, pas d'histogramme. |
| **B** | Tableau de bord | Aucun objet privilégié, tout en un écran. Une ligne par objet, dot plot dépouillé → projeté. |
| **C** | Cartes d'abord | La carte plein cadre, onglets, chiffre en surimpression. La seule en carte Mapbox. |
| **D** | Soirée électorale | Fond sombre, chiffres énormes, pensée pour être projetée ou regardée de loin. |
| **E** | Écart à la majorité | « À 3,1 points » plutôt que « 46,9 % ». Axe centré sur 50 %, la correction de l'extrapolation rendue visible. |

`index.html` les liste ; chaque fichier porte son parti pris en commentaire en
tête. Elles partagent les mêmes données et les mêmes figures : ce qui les
sépare est un choix, pas un hasard.

## Les fichiers

| Fichier | Rôle | Versionné |
|---|---|---|
| `construire.py` | génère tout ce qui suit depuis la base fictive, avec les fonctions du site | oui |
| `simplifier_geojson.py` | allège les contours communaux (Douglas-Peucker + arrondi) | oui |
| `charte.js` | **les réglages de design**, appliqués par-dessus les figures au chargement | oui |
| `topojson-stub.js` | évite que Plotly aille chercher un fond de carte mondial sur le réseau | oui |
| `verifier.js` | affiche un bandeau lisible quand les fichiers générés manquent | oui |
| `accueil-*.html`, `index.html` | les variantes et leur sommaire | oui |
| `capture.mjs` | capture PNG d'une variante (Playwright), pour discuter par message | oui |
| `figures.js` | contrat de vue + figures en JSON (`window.VUE`, `FIGURES`, `GEOJSON`) | **non** (généré, 1,8 Mo) |
| `plotly.min.js` | plotly.js, copié du paquet Python — la version qui a produit les figures | **non** (généré) |
| `communes-simplifie.geojson` | contours allégés | **non** (généré) |
| `pret.js` | témoin de construction, lu par le sommaire | **non** (généré) |

Pour changer l'apparence d'un graphe, on édite `charte.js` (ou la surcharge
`THEME` en tête de chaque variante) et on recharge. **On n'édite jamais
`figures.js`** : il sort de `graphiques.py` et `carte/`, comme les figures du
site, et c'est ce qui garantit que la maquette ne promet rien que Django ne
donnerait pas.

## Ce qu'une variante a le droit de demander

Une variante peut proposer une figure que le site ne produit pas encore — E
en est le cas : son axe centré sur la majorité n'existe nulle part dans
`graphiques.py`. C'est légitime, et c'est même le but : la maquette sert à
découvrir ce qu'il faudrait construire. La règle reste la même — la figure
sera **ajoutée à `graphiques.py`**, jamais bricolée dans `figures.js`. De
même, une variante qui réclamerait une donnée absente du contrat de vue passe
par la voie Moteur et par `tests/test_contrat.py`.

## Deux détails techniques qui ont coûté du temps

**Les cartes SVG et le réseau.** `px.choropleth` demande à plotly.js un fond
de carte mondial, qu'il télécharge sur `cdn.plot.ly`. La requête échoue en
`file://` — d'où des cartes vides — et casserait le miroir statique
hors-ligne. Nos cartes n'en affichent pourtant rien (`geo.visible = false`).
`topojson-stub.js` dépose une topologie vide dans le cache que plotly.js
consulte avant de télécharger. À reprendre côté site si la carte SVG est
retenue.

**Le cadrage.** La projection SVG cadre toute seule sur les données
(`fitbounds`). Mapbox garde le zoom figé à la construction : la variante C
doit le recalculer en fonction de la taille du cadre. C'est un argument de
plus dans la comparaison des deux (Partie 7.1).

## Captures

```bash
node maquette/capture.mjs maquette/accueil-c.html c.png        # grand écran
node maquette/capture.mjs maquette/accueil-c.html c-tel.png 400  # téléphone
```

Le PNG sert à discuter par message, jamais de support de travail : c'est la
page qu'on regarde.
