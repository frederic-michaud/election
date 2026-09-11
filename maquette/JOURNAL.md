# Journal de bord des maquettes

Ce qu'on a essayé, ce qu'on a décidé, et pourquoi. Une entrée par séance de
travail, la plus récente en haut. Le README dit *comment* la maquette marche ;
ce journal dit *ce qu'on en a fait*.

Règle de tenue : chaque changement dans `maquette/` fait un commit, et chaque
séance laisse une entrée ici, même courte. C'est l'historique de conception —
celui qui n'ira jamais dans `master`, mais qu'on veut pouvoir relire dans un an
pour savoir pourquoi la page ressemble à ce qu'elle est.

## 2026-09-11, suite — La barre noire change de côté ; deux traits qui se ressemblent

**Point de départ.** Deux suggestions. Sur C1, mettre la barre noire toujours
du côté opposé à la flèche, pour qu'on voie la flèche : elle part donc parfois
de la gauche, parfois de la droite. Et un problème qu'on voit partout : le
trait du dépouillé et celui de la majorité se ressemblent, ce qui rend les
graphiques difficiles à lire — explorer différentes options.

**Ce qu'on a fait.**

- *C1.* La barre part de la gauche quand la projection monte, de la droite
  quand elle descend. La flèche est toujours sur le rail gris, jamais sur la
  barre : elle redevient noire, comme sur les autres formes. Le prix, noté
  dans la carte : quand la barre part de la droite, sa longueur est la part de
  *non* — seule son extrémité compte, et il faut le savoir.
- *Une nouvelle planche, `barres-reperes.html`.* Huit options pour distinguer
  les deux traits, sur la forme C2, avec les quatre scénarios et le curseur,
  plus l'état actuel (R0) pour comparer. Quatre travaillent la majorité :
  pointillé (R1), filet gris pleine hauteur (R2), triangle sous le rail (R3),
  rail teinté rouge/bleu de part et d'autre de 50 (R4). Quatre travaillent le
  dépouillé : losange (R5), épingle (R6), pilule épaisse contre majorité fine
  (R7), rail interrompu à 50 (R8). Une option de chaque groupe se combine.

**Décisions.**

- *La planche n'applique rien aux autres pages.* On choisit d'abord, on
  reporte ensuite — sur `barres-intervalle.html`, puis sur D′.
- *Les options changent une seule chose à la fois*, le trait du seuil ou celui
  de la valeur, pour qu'on compare des repères et pas des styles.

**Ce qu'on a vu.** R2 (filet gris pleine hauteur) est le plus lisible : la
majorité devient le décor, la seule chose noire et courte est la donnée, et
sur une page entière les filets alignés forment une colonne à 50. R6
(épingle) est le meilleur côté dépouillé : le trait garde sa précision, la tête
dit « ici ». R4 (rail teinté) répond le plus directement à la question « la
zone passe-t-elle 50 ? » sans aucune ligne. R3 et R8 s'effacent dans les cas
serrés, ceux qu'on veut justement lire ; R5 fait revenir une forme ronde
qu'on vient de chasser. Combinaison à essayer en premier : R2 + R6.

**Ouvert.** Choisir un repère, ou une paire, et le reporter partout.

## 2026-09-11, toujours — Plus de pastille : la question, c'est 50 %

**Point de départ.** Refaire toutes les variations sans la pastille centrale.
Le chiffre suffit à dire où est le projeté ; ce qui intéresse le lecteur, c'est
de voir si l'intervalle de confiance passe par-dessus 50 %. La position exacte
de l'extrapolation n'est pas si importante, et déjà lisible dans le chiffre.

**Ce qu'on a fait.** La planche est réécrite sans aucune pastille. Le trait du
dépouillé, le trajet, la zone et les deux chiffres restent. Sans pastille, la
zone devient l'unique objet coloré de l'haltère : l'œil va droit à la question
« chevauche-t-elle le trait de majorité ? ». Le trait de majorité est renforcé
(opacité 0,7) puisqu'il est désormais la référence. Quand le dépouillé est
dans la marge, plus de fil gris non plus : il pointait vers un centre qu'on ne
dessine plus.

Deux variations changent de sens, « sans pastille » et « anneau » n'ayant plus
d'objet :

- *C8 — Acquis, refusé, en jeu.* Trois états, trois couleurs : l'intervalle
  entier est bleu s'il est tout au-dessus de 50, rouge s'il est tout en
  dessous, gris et marqué « en jeu » s'il passe par-dessus — et le chiffre
  prend la même couleur. Le verdict n'est affiché que quand l'intervalle le
  garantit.
- *C9 — Axe resserré, 25–75.* Le C2 sur un axe qui ne va plus de 0 à 100 :
  tout est deux fois plus large, l'intervalle de fin de soirée redevient
  visible. Un résultat de votation fédérale vit entre 25 et 75.

**Décisions.**

- *Pas de pastille, nulle part.* Le chiffre est le projeté. La zone marque
  l'intervalle, et son centre suffit à l'œil.
- *Le trait de majorité est la référence de lecture.* Il apparaît dans chaque
  légende.
- *C7 et C8 disent la même chose avec deux tempéraments.* C7 nuance (la part de
  chaque couleur dit combien c'est serré) ; C8 tranche (verdict ou « en jeu »,
  rien entre). C8 est le plus prudent : il refuse de colorer 51 % en bleu tant
  que la marge touche 50, et son gris devient bleu quand la marge se resserre
  — le déroulé d'une soirée.

**Ce qu'on a vu.** Sans pastille, C3 (bande pleine) et C6 (deux niveaux)
gagnent en netteté ; C4 (moustaches) devient un crochet fin, toujours
fragile ; C5 (fondu) rend la question « passe-t-il 50 ? » floue par nature.
Les plus convaincants : C2 pour la simplicité, C7 et C8 pour la question de
la majorité, C9 pour la fin de soirée.

**Ouvert.** Si une forme à intervalle est retenue, la marge devient une
demande ferme à la voie Moteur, et C8 a besoin qu'elle soit honnête : c'est
elle qui décide du mot affiché.

## 2026-09-11, encore — La fin du dépouillement, l'état oublié

**Point de départ.** Remarque juste : les variations à intervalle étaient
trompeuses, parce qu'elles n'étaient jugées que sur le début de soirée, quand
le dépouillé est loin du projeté. À la fin — et c'est l'état où la page passe
le plus clair de son temps — le dépouillé tombe *dans* l'intervalle, la
correction est plus petite que la marge, et plusieurs formes s'effondrent :
la pastille écrase le trait, la flèche n'a plus de sens, rien ne dit que c'est
un bon signe. Demande : ajouter ce scénario et reprendre les propositions.

**Ce qu'on a fait.**

- *Un quatrième scénario, fictif et annoncé comme tel* : « fin du
  dépouillement, 96 % des communes », 50,7 % dépouillé, 51,0 % projeté, marge
  × 0,5 — le dépouillé est dans l'intervalle quelle que soit la position du
  curseur, et l'intervalle chevauche 50 à la marge par défaut. Il n'est pas
  dans `figures.js` : il est écrit dans la page, séparé des trois vrais par un
  filet et un nom en bleu.
- *Une règle commune aux neuf formes pour cet état* : le trait du dépouillé
  passe toujours au-dessus de la pastille, avec un halo blanc, et la dépasse en
  hauteur — il reste visible même quand ils coïncident. Plus de flèche quand
  le dépouillé est dans la marge : un fil gris relie encore les deux (on voit
  qu'il reste un écart, et qu'il est plus petit que la marge), et l'étiquette
  le dit en toutes lettres, « dépouillé dans la marge ». Dans C1, la barre
  noire garde un trait à son extrémité pour ne pas disparaître sous la pastille.
- *Une neuvième variation, C9, l'anneau*, pensée pour cet état : la pastille
  est un anneau, le trait et la zone restent visibles à travers, et à la fin
  l'anneau entoure le trait — « le compté est dans le cercle », sans flèche ni
  mot.
- *Chaque note dit maintenant comment la forme se comporte à la fin.*

**Ce qu'on a vu, forme par forme, à la fin du dépouillement.**

- Tiennent : *C2* (trait dans la zone hachurée, l'image tient seule), *C7*
  (l'intervalle bicolore dit « probable, pas acquis », et devient tout bleu
  quand c'est plié), *C8* (sans pastille, rien ne se cache), *C9* (l'anneau
  entoure le trait).
- Se dégradent : *C1* (l'image « une barre qui pointe vers une zone » n'a plus
  lieu d'être — forme de début de soirée), *C3* (la bande claire disparaît
  sous la pastille, l'idée d'intervalle avec elle), *C5* (joli halo, mais
  « dans la marge » ne se distingue pas de « tout près »), *C6* (les deux
  niveaux se confondent).
- À écarter : *C4* (quatre traits verticaux dans quelques pixels).

**Décision.** Toute proposition de barre se juge désormais sur les deux états,
début et fin de soirée. Le scénario fictif reste sur la planche tant que le
contrat de vue ne fournit pas de marge réelle.

## 2026-09-11, plus tard — L'haltère C avec un intervalle de confiance

**Point de départ.** Sur la planche des barres, c'est C (l'haltère avec sens)
qui plaît. Demande : y ajouter un intervalle de confiance, sur une nouvelle
page, en gardant `barres.html` tel quel. Exemple donné : une barre noire pour
la valeur initiale, qui pointe vers une zone hachurée, l'intervalle.

**Ce qu'on a fait.** `barres-intervalle.html`, huit variations de C avec un
intervalle autour du projeté. La première (C1) est l'exemple donné, mot pour
mot ; les suivantes déclinent la forme de l'intervalle.

- *C1 — Barre noire vers la zone hachurée.* Le dépouillé est une barre pleine
  depuis 0, la flèche va au bord de l'intervalle.
- *C2 — Trait vers la zone hachurée.* Le trait de C, la flèche noire.
- *C3 — Bande pleine, en clair.* Bleu clair = extrapolé, comme sur les cartes.
- *C4 — Moustaches.* La barre d'erreur des scientifiques.
- *C5 — Fondu.* Pas de bord : une densité qui décroît.
- *C6 — Deux niveaux.* Probable au centre, possible autour.
- *C7 — La majorité en jeu.* L'intervalle hachuré change de couleur à 50 :
  bicolore quand la majorité est encore en jeu.
- *C8 — Sans pastille.* Le projeté n'est pas un point, on ne le dessine pas.

**Décisions.**

- *La marge est inventée, et dite telle.* Le site ne la calcule pas ; la page
  l'annonce en tête et au pied. Un curseur (± 1 à ± 8) la fait varier, et un
  facteur par objet (× 0,7, × 1, × 1,4) donne à voir un intervalle étroit et
  un large sur la même page.
- *La flèche vise le bord de l'intervalle, pas la pastille.* C'est ce que
  l'exemple demandait, et c'est plus juste : on corrige vers une zone. Quand le
  dépouillé est déjà dans l'intervalle, il n'y a pas de flèche du tout — c'est
  une information.
- *Dans C1, la flèche prend la couleur du verdict* : quand la projection
  descend, elle revient sur la barre noire et une flèche noire y disparaîtrait.
  Partout ailleurs, elle est noire, comme le trait : les faits en encre, le
  verdict en couleur.

**Ce qu'on a vu.** À ± 3 la zone hachurée est presque cachée par la pastille
(15 px) ; elle prend son sens à partir de ± 4 ou sur écran large. Si une
variante à intervalle est retenue, réduire la pastille ou la creuser en anneau.
C7 est la plus parlante sur le cas qui fâche : à ± 5, LTr devient à moitié
bleu, à moitié rouge.

**Ouvert.** Quelle forme d'intervalle, et faut-il une vraie marge ? Si oui,
c'est une demande à la voie Moteur (une marge par objet dans le contrat de
vue), et `tests/test_contrat.py` suit.

## 2026-09-11 — Planche : dix barres pour un dépouillé et un projeté

**Point de départ.** Les barres de la variante B plaisent : montrer sur une
même barre le résultat dépouillé et le résultat projeté. Deux réserves : il
faut savoir en un coup d'œil lequel est quoi (une légende n'est pas exclue),
et la couleur pose problème quand les deux ne tombent pas du même côté de la
majorité. Demande : dix maquettes de barres sur une seule page, à part des
variantes, deux ou trois standard et le reste plus audacieux, pour brainstormer.

**Ce qu'on a fait.** `barres.html`, une *planche* — pas une variante : des
composants isolés, listés dans une nouvelle section « Planches » du sommaire.
Dix cartes, chacune avec son parti pris, sa légende, les trois objets du jour
et une note sur la question des couleurs. Sans Plotly : du CSS, avec les
données de `figures.js` pour rester sur les vrais chiffres. Les données du
jour fournissent justement le cas qui fâche : LTr, 54,4 % dépouillé → 46,9 %
projeté, le dépouillé dit oui et la projection dit non.

**Les dix, en une ligne chacune.**

- *A — Deux barres, une légende.* Un rang dépouillé (encre), un rang projeté
  (couleur du verdict). Standard.
- *B — Une barre, un repère.* Le « bullet chart » : la barre est le projeté, le
  dépouillé un trait noir posé dessus. Standard.
- *C — Haltère avec sens.* Le dot plot de B, plus une pointe sur le trajet.
  Standard.
- *D — Plein contre pointillé.* Plein = compté, pointillé = estimé, sur le
  même rang : ce qui déborde du cadre est ce que l'extrapolation retire.
- *E — Depuis la majorité.* La barre part de 50, vers la gauche (rouge) ou la
  droite (bleu) : l'écart à la majorité, pas le pourcentage. L'idée de E.
- *F — La flèche de correction.* Barre du projeté, et au-dessus une flèche
  noire qui part du dépouillé : on voit d'où l'on vient.
- *G — Sur l'échelle de la carte.* La barre est la légende des cartes
  (rouge → neutre → bleu), les deux valeurs sont des marques noires dessus.
- *H — Ce qui manque, ce qui dépasse.* Gris jusqu'à la valeur ou jusqu'à 50 ;
  la couleur ne peint que la distance à la majorité.
- *I — Thermomètres.* Vertical, par paires, la majorité en travers ; il faut
  des sigles.
- *J — La fourchette.* Le projeté est une plage, pas un point ; marge
  inventée (± 3) pour poser la question de l'incertitude.

**Trois réponses au problème des couleurs**, qui traversent les dix :

1. *Un seul des deux porte une couleur* (A, B, C, D, F, J) : le dépouillé est
   un fait, en encre ; le projeté seul porte le verdict. Pas de conflit
   possible, puisqu'il n'y a qu'un verdict affiché.
2. *La couleur vient du côté, pas du verdict* (E, H) : à gauche de 50 rouge,
   à droite bleu, toujours. Le cas qui fâche devient le plus lisible.
3. *La couleur est sous les marques, pas sur elles* (G) : la barre est
   l'échelle de la carte, les valeurs sont noires et se lisent contre elle.

**Décisions.**

- *Une planche, pas une variante.* Le sommaire gagne une section « Planches »
  pour les composants isolés ; on ne touche pas aux variantes.
- *Les chiffres au bout des barres sont posés sur une pastille blanche*, sinon
  ils se lisent mal sur le trait de majorité — le cas de toute valeur entre 40
  et 50, fréquent.
- *Les étiquettes centrées s'ancrent au bord* quand la valeur est sous 12 ou
  au-dessus de 88, pour ne pas sortir de la barre.

**Ouvert.** Choisir, ou mélanger — par exemple B ou F pour le rang, avec la
couleur de E. Et, si J plaît, demander une marge à la voie Moteur. La page se
regarde aussi en colonne unique sur téléphone : chaque carte y tient.

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

**Et sur téléphone, l'emblème seul.** Sous 600 px — le seuil du site pour
cacher son titre — le nom « Politiques.ch » disparaît de l'en-tête, le logo
reste. Le point rouge reste dans la barre d'avancement : validé tel quel.
La date, elle, reste à côté du logo au lieu de passer dessous : l'en-tête ne
replie plus, et « Votation fédérale » / « du 10 septembre 2026 » se coupent en
deux lignes alignées à droite.

**Le bloc de dépouillement se fait petit sur téléphone.** L'essentiel, ce sont
les objets ; le taux de dépouillement est utile d'emblée, pas central. Sous
600 px le bloc passe de 148 à 79 px : le direct sur une ligne, puis la jauge
avec son pourcentage à droite, en 1,1 rem. L'étiquette « Dépouillement »
disparaît, « Dépouillement en cours » la rend redondante. Grand écran
inchangé — la proportion y est bonne. Au passage : le bloc `@media` doit rester
en fin de feuille, sinon les règles de base, écrites après, l'écrasent.

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
