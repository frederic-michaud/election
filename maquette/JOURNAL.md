# Journal de bord des maquettes

Ce qu'on a essayé, ce qu'on a décidé, et pourquoi. Une entrée par séance de
travail, la plus récente en haut. Le README dit *comment* la maquette marche ;
ce journal dit *ce qu'on en a fait*.

Règle de tenue : chaque changement dans `maquette/` fait un commit, et chaque
séance laisse une entrée ici, même courte. C'est l'historique de conception —
celui qui n'ira jamais dans `master`, mais qu'on veut pouvoir relire dans un an
pour savoir pourquoi la page ressemble à ce qu'elle est.

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
