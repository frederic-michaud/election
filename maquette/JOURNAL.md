# Journal de bord des maquettes

Ce qu'on a essayé, ce qu'on a décidé, et pourquoi. Une entrée par séance de
travail, la plus récente en haut. Le README dit *comment* la maquette marche ;
ce journal dit *ce qu'on en a fait*.

Règle de tenue : chaque changement dans `maquette/` fait un commit, et chaque
séance laisse une entrée ici, même courte. C'est l'historique de conception —
celui qui n'ira jamais dans `master`, mais qu'on veut pouvoir relire dans un an
pour savoir pourquoi la page ressemble à ce qu'elle est.

## 2026-09-10, plus tard — D′ retenue ; fonds inversés, logo, moins de texte

**Point de départ.** D′ est la variante qui plaît le plus : c'est désormais la
base de travail, les autres restent en comparaison. Trois retouches demandées
avant des changements plus profonds.

**Ce qu'on a fait.**

- *Fonds inversés.* La page passe en crème (`#fcfcfb`), les panneaux en blanc
  pur. La surface des figures suit les panneaux (`THEME.surface`), donc le
  filet entre communes est blanc lui aussi.
- *Le logo revient.* L'emblème du site (`scrutin/static/scrutin/logo.png`) est
  un PNG gris et bleu ciel : la Suisse, quatre barres qui en sortent, des
  points, « Politiques.ch » à la verticale. La maquette en refait une version
  SVG en ligne, dans sa palette, posée à gauche du nom dans l'en-tête.
- *Le résumé « 1 objet accepté sur 3 » est retiré* de la barre d'avancement,
  qui ne dit plus que la date de la votation.

**Décisions.**

- *Un SVG plutôt que le PNG.* Il suit les variables CSS (le gris des encres,
  le bleu des oui), reste net à toute taille, et pèse 3 Ko en ligne dans la
  page — pas de fichier à part, pas de binaire.
- *La silhouette vient des données, pas d'un dessin.* `logo.py` prend le
  contour extérieur des communes de `data/K4voge_*.geojson` (les arêtes qui ne
  bordent qu'une commune), le projette et le simplifie avec le Douglas-Peucker
  de `simplifier_geojson.py`. Aucune dépendance. Les lacs, qui ne sont pas des
  communes, ressortent d'eux-mêmes : Neuchâtel en trou, Léman et Constance en
  échancrures ; les petits lacs sont ignorés (moins de 0,4 % du pays).
- *L'idée est gardée, la typographie non.* Le mot à la verticale du PNG ne
  tient pas dans un en-tête d'une ligne : l'emblème (carte, barres, points) est
  conservé, « Politiques.ch » est posé à côté, en romain, le « .ch » en bleu
  comme avant.

**Puis, dans la foulée : date et direct permutés.** « Votation fédérale du
10 septembre 2026 » monte dans l'en-tête, « Dépouillement en cours · heure »
descend dans la barre d'avancement. Les styles, eux, ne bougent pas : capitales
espacées à l'en-tête, petit texte gris dans la barre. Le point rouge qui pulse
suit le direct, puisque c'est lui qu'il signale — à reprendre si on le voulait
à l'en-tête.

**Ce qu'on a vu.** À 48 px de haut, l'emblème se lit : la carte, les barres,
les trois points. Le trou du lac de Neuchâtel est un détail qu'on devine plus
qu'on ne le voit — c'est bien.

**Ouvert.** Le PNG d'origine reste disponible si l'on préfère : une balise
`<img src="../scrutin/static/scrutin/logo.png">` à la place du SVG. Le neutre
des cartes, désormais sur blanc, reste à revoir (voir plus bas).

## 2026-09-10 — D′, la soirée électorale sur fond clair

**Point de départ.** La variante D (« Soirée électorale ») plaît. La question
posée : qu'est-ce que ça donne sur fond blanc ?

**Ce qu'on a fait.** Une déclinaison `accueil-d-clair.html`, copie de D au
pixel près où seule la palette change. Ajoutée au sommaire (`index.html`) et
au README sous la lettre D′.

**Décisions.**

- *Un fichier séparé plutôt qu'un bouton sombre/clair dans D.* Une variante par
  fichier, c'est la convention du dossier : on ouvre les deux côte à côte, et le
  `passeur` n'a qu'un fichier à lire le jour où l'on tranche.
- *La palette de `charte.js` telle quelle, pas une version éclaircie de D.* D
  avait dû éclaircir ses bleus et rouges pour tenir sur la nuit ; le fond clair
  permet de revenir aux couleurs validées (Partie 7 du plan). Fond de page blanc
  pur, panneaux `#fcfcfb` à filet `#e1e0d9` — la surface des figures et celle
  des panneaux sont les mêmes.
- *Les réglages de carte de D sont conservés* : 210 px de haut, sans barre de
  couleur, demi-étendue 18, contour 0,15.

**Ce qu'on a vu.**

- Les chiffres énormes tiennent très bien en bleu/rouge sur blanc ; la page
  reste un « mur de résultats ».
- Les cartes perdent du relief : le neutre de l'échelle divergente (`#f0efec`)
  est presque la couleur du panneau, donc les communes proches de 50 % se
  fondent dans le fond. Sur la nuit de D, ce milieu restait un gris visible.
  Si le clair est retenu : assombrir un peu `neutre` dans le bloc `THEME`, ou
  marquer davantage le contour entre communes. À trancher en regardant.
- Tient en fenêtre étroite (375 px) sans retouche.

**Ouvert.** Sombre ou clair ? Le sombre donne la solennité de la soirée ; le
clair, la lisibilité de jour et une palette déjà validée. Pas encore tranché.

**Outillage.** Aucun Chrome ni Chromium sur la machine de travail : `capture.mjs`
ne tourne pas sans `npx playwright install chrome`. Les pages ont été regardées
dans un navigateur à travers un petit serveur statique (`python3 -m http.server`
sur `maquette/`), parce que ce navigateur-là refuse les `file://`.
