# Cahier de passage — D′ vers `master`

À lire **en premier** par l'agent `passeur` (`.claude/agents/passeur.md`), avant
toute autre page du dossier. Il dit ce qui a été validé, ce qu'il faut
transposer, ce que la maquette invente et que le site n'a pas, et ce qui reste à
trancher. Le `README.md` dit comment la maquette marche ; le `JOURNAL.md` dit
pourquoi elle ressemble à ce qu'elle est.

## Statut

**Passage fait deux fois le 2026-09-13, à départager** : #44 (cartes SVG) et
#46 (cartes WebGL zoomables, sur #45 pour l'heure et la langue). Fourchette à
±2,5 points faute d'intervalle de confiance (#43).

**D′ (`accueil-d-clair.html`) est validée à deux, le 2026-09-13, comme version
finale pour cette release** — la votation fédérale du **27 septembre 2026**.

- La référence est l'état de `accueil-d-clair.html` et `charte.js` au commit qui
  introduit ce fichier (`git log -- maquette/PASSAGE.md`). Toute retouche
  ultérieure de la maquette devra mettre ce cahier à jour.
- Les critères d'arrêt de la Partie 7.2 du plan sont remplis, sauf un : la
  **palette n'est pas passée par `validate_palette.js`**, qui n'existe pas dans
  le dépôt. Le rouge du « non », `#c9352b`, ne figure pas dans les paires que le
  plan donne pour validées. À faire en 7.3, sans rouvrir la maquette.

## Par où commencer

1. Ce cahier.
2. `accueil-d-clair.html` : le `:root`, l'objet `THEME`, le balisage, la
   fonction `barre()`. C'est **le seul fichier de variante à transposer**.
3. `charte.js` : les réglages Plotly, à transcrire dans `scrutin/charte.py`.
4. `JOURNAL.md`, entrées du 2026-09-10 (« D′ ») au 2026-09-13 : le pourquoi de
   chaque choix, si un détail résiste.

Ne pas transposer : les variantes A, B, C, D, E, les planches `barres*.html`,
`verifier.js`, `pret.js`, `construire.py`, `capture.mjs`.

**Mise en place.** Si `maquette` est déjà extraite dans le clone principal, le
`git worktree add ../election-maquette maquette` du passeur échoue (« already
checked out »). Faire l'inverse : `git worktree add ../election-master master`,
ou repasser le clone principal sur `master` d'abord.

## Décisions actées

| Sujet | Décision |
|---|---|
| Variante | **D′**, la soirée électorale sur fond clair. A, B, C, D, E écartées. |
| Carte | **Projection SVG** (`px.choropleth`), pas Mapbox : tranche la question 7.2. Mercator, axes bornés à l'emprise des communes, hauteur donnée par les proportions du pays. Sans barre de couleur. |
| Échelle de la carte | Divergente rouge `#c9352b` → neutre `#f0efec` → bleu `#2a78d6`, centrée sur 50 %, bornée à 32–68 % (`demiEtendue: 18`). Contour de 0,15 px dans la couleur du panneau, opacité 1. Le neutre sur blanc est **validé tel quel**. |
| Histogramme | **Aucun** sur l'accueil. |
| Chaque objet | Un panneau : le nom, les deux valeurs, la barre finale, la carte. |
| Les valeurs | L'extrapolé en grand, dans la couleur du verdict, pastille « extrapolé » et fourchette à sa droite (« fourchette » puis « 44,8 – 49,0 % », bornes jamais coupées). Le dépouillé en petit gris, pastille « dépouillé », calé sur la fin de la barre. |
| Le verdict | Porté par la couleur seule (bleu ≥ 50 %, rouge sinon). **Plus de pastille « accepté / refusé ».** |
| La barre | Sans aucun texte. Rail rouge pâle / bleu pâle de part et d'autre de 50 ; moustache (intervalle de confiance) dans la couleur du verdict ; dépouillé en trait gris avec flèche vers l'intervalle, **seulement s'il est hors de l'intervalle**. Un `aria-label` porte les valeurs. |
| En-tête | Logo SVG en ligne (emblème tiré des contours, voir `logo.py`) et « Politiques.ch », le « .ch » en bleu ; à droite « Votation fédérale du … » en petites capitales. Sous 600 px : le nom disparaît, la date passe sur deux lignes à côté du logo. |
| Avancement | Pourcentage dépouillé, jauge, point rouge qui pulse et « Dépouillement en cours · heure ». Compact sous 600 px. |
| Menu | **En pied de page, plus dans l'en-tête** : « Accueil », puis les pages statiques dans leur ordre en base. La page courante porte `aria-current="page"`. Plus de menu hamburger, plus de Font Awesome. |
| « Cartes » | **Retiré du menu.** Le sort de la vue `/cartes` elle-même n'est pas tranché. |
| Copyleft | **Pas de mention en pied de page** pour cette release. |
| Mobile | Colonnes en `minmax(min(300px, 100%), 1fr)` ; sous 360 px, 14 px de marge de page et 16 px dans les panneaux. |

## Correspondance maquette → site

| Dans la maquette | Sur `master` | Remarques |
|---|---|---|
| `:root` de D′ | variables CSS de `scrutin/static/scrutin/style.css` | Une seule fonte, la sans système. Le bloc `@media` en fin de feuille, sinon les règles de base l'écrasent. |
| En-tête, logo, date | `templates/base.html` | `lang="fr"`. Le logo reste un SVG en ligne. |
| Pied de page | `templates/base.html` | `{% url 'home' %}` puis la boucle existante sur `pages_statiques`, déplacée. `aria-current` selon la page servie : ce n'est pas du contenu dépendant du visiteur, le cache nginx n'est pas concerné. |
| Avancement, mur, panneaux, valeurs | `templates/home.html` | Les constantes de `figures.js` remplacées par le contrat de vue. |
| `barre()` (JS) | calcul côté serveur, dans la zone Interface | Des pourcentages en `style="left:…%;width:…%"` : pas de JS nécessaire. Le calcul reste hors de `donnees.py` et hors de `views.py`, qui doit rester minuscule. |
| `THEME` et `charte.js` | `scrutin/charte.py`, appliqué à la figure SVG | Voir « Pièges » pour la projection et l'emprise. |
| `figure_carte_svg`, `figure_*`, `en_div` | `carte/API.py`, `scrutin/graphiques.py` | Écrits en 7.1, **présents seulement sur la branche `maquette`** : à réécrire sur `master`, sans *cherry-pick*. |
| `plotly.min.js` | vendoré dans les statiques | La version du paquet Python (plotly.js **3.7.0** avec `plotly==6.*`), à la place du CDN 2.11.1 de `base.html`. |
| `topojson-stub.js` | statique, chargé avant les figures | Sans lui, la carte SVG va chercher un fond de carte mondial sur `cdn.plot.ly`. |
| Configuration Plotly | `displayModeBar: false`, `responsive: true` | |
| Formats | « 46,9 % », « 10 septembre 2026 », « 15:11 » | Virgule décimale, espace insécable avant « % » et entre les bornes. |

## Ce que la maquette invente — demandes à la voie Moteur

Rien de ceci ne se va chercher dans l'ORM : chaque point passe par le contrat de
vue et `tests/test_contrat.py`, des deux côtés.

1. **L'intervalle de confiance par objet.** La fourchette et la moustache
   reposent sur des marges **inventées** (`MARGES = [2.1, 3, 4.2]`). Le contrat
   n'en porte pas ; c'est la tâche D1, « IC par bootstrap ». **Bloquant pour la
   barre et la fourchette.** Jamais de marge inventée en production.
2. **L'heure de la dernière projection.** La maquette affiche l'heure du
   navigateur (`new Date()`). Le site, mis en cache, doit afficher le
   `moment_creation` de la dernière `Extrapolation` : un champ à ajouter au
   contrat.
3. **La langue et le fuseau.** `settings.py` est en `LANGUAGE_CODE = 'en-us'`
   et `TIME_ZONE = 'UTC'` : mois en anglais et heure décalée de deux heures.
   Il faut `fr` (ou `fr-ch`) et `Europe/Zurich`. `settings.py` est en zone
   Moteur.
4. **L'état du dépouillement**, si « terminé » doit se distinguer de « en
   cours » (voir plus bas) : `avance == 1` suffit peut-être, à confirmer.

**À trancher à deux, avant d'écrire la barre** : si l'intervalle n'est pas prêt
pour le 27 septembre, soit on attend, soit on publie D′ sans fourchette ni
moustache. Cette version dégradée n'a pas été dessinée ni validée.

## États que la maquette ne montre pas

La maquette ne dessine qu'une soirée en cours à 15,7 %, avec trois objets aux
noms courts. Ces cas-là se présenteront et **ne doivent pas être inventés
seul** : les signaler et les faire trancher.

- **Dépouillement terminé** (100 %) : le point qui pulse et « en cours » n'ont
  plus de sens.
- **Avant les premiers résultats.** Sous 7 communes, `get_extrapolation`
  renvoie 50 % : la page afficherait « 50,0 % » en bleu.
- **Hors soirée de vote.** Entre deux votations, l'accueil montre la dernière,
  toujours « en cours ».
- **Un nombre d'objets autre que trois.** La grille s'adapte, mais seul le cas
  à trois a été regardé.
- **Des noms d'objet réels, longs** (« Initiative populaire « … » »). Le nom a
  un `min-height` de `3em`, deux lignes, et les noms fictifs y tiennent. Un nom
  sur quatre lignes décalerait les valeurs d'un panneau à l'autre.
- **Les autres pages** (Méthodes, Contact, `/pca`, `/cartes`) héritent de
  l'en-tête et du pied de page ; leur contenu n'a pas été dessiné. Attention,
  `carte_view` rend aujourd'hui `home.html` : la réécriture de ce gabarit la
  touchera.
- **Le niveau de confiance** : afficher « fourchette à 95 % » ou le laisser à
  la page Méthodes. À décider quand l'intervalle sera réel.

## Pièges déjà rencontrés

- **La carte écrasée.** `px.choropleth` laisse Plotly en équirectangulaire, et
  la Suisse sort 2,28 fois plus large que haute, pour 1,56 en réalité. Il faut
  `projection: {type: "mercator"}`.
- **La carte qui flotte.** En Mercator, `fitbounds` cale le pays dans le cadre
  *carré* de la projection entière : 58 % de la largeur seulement. Il faut
  `fitbounds: false`, avec `lonaxis.range` et `lataxis.range` bornés à l'emprise
  des contours (plus 0,5 % de la largeur). La maquette la calcule dans le
  navigateur (`emprise()` dans `charte.js`). **Côté site, la calculer en
  Python**, une fois : si la PR #40 est fusionnée, le GeoJSON n'est plus dans la
  figure mais servi par URL, et le navigateur ne l'a pas sous la main au moment
  du tracé.
- **La hauteur.** Pas de `layout.height` : `aspect-ratio: 1.55` sur le
  conteneur, et Plotly prend sa hauteur. Proportions vérifiées à 1,56 à toutes
  les largeurs.
- **Les tailles de police.** Les chiffres, les pastilles et la fourchette sont
  dimensionnés sur la largeur du panneau (`cqi`, `container-type:
  inline-size`), avec une première déclaration en repli pour les navigateurs
  sans requêtes de conteneur.
- **Les classes.** La barre est préfixée `.barre` : `.chiffre`, `.carte` et
  `.rail` existent déjà ailleurs dans la page.
- **La PR #40**, « contours par URL statique », est ouverte et touche
  `carte/API.py`. Savoir si elle passe avant ou après le passage, pour ne pas
  réécrire la carte deux fois.

## Contrôle avant de proposer

- Le site et D′ côte à côte, à **1200 et 400 px** comme le demande
  `passeur.md`. Ajouter **320 px** (les débordements du mobile y
  apparaissaient) et **1000 px** (trois colonnes étroites, la seconde rangée des
  valeurs au plus serré). Les mêmes points que la maquette : marges égales à
  gauche et à droite, valeurs dans le panneau et côte à côte, cartes à 1,56,
  menu sur une ligne, aucun débordement horizontal.
- `ruff check .` et `pytest`. `test_la_page_d_accueil_s_assemble` cherche
  « plotly » dans la page : les cartes suffisent, l'histogramme n'est plus là.
- **Le plan, dans la même PR** : cocher 7.2 (variante validée, SVG tranché,
  téléphone), noter la palette encore à valider, et réécrire la « Cible
  visuelle » avec ce qui a été retenu (7.3).
