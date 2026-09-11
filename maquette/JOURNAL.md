# Journal de bord des maquettes

Ce qu'on a essayé, ce qu'on a décidé, et pourquoi. Une entrée par séance de
travail, la plus récente en haut. Le README dit *comment* la maquette marche ;
ce journal dit *ce qu'on en a fait*.

Règle de tenue : chaque changement dans `maquette/` fait un commit, et chaque
séance laisse une entrée ici, même courte. C'est l'historique de conception —
celui qui n'ira jamais dans `master`, mais qu'on veut pouvoir relire dans un an
pour savoir pourquoi la page ressemble à ce qu'elle est.

## 2026-09-11, nuit, suite — D′ allégé : les chiffres au-dessus, la barre sans texte

**Point de départ.** Avec la barre finale, les panneaux de D′ font très
chargés. Trois demandes :

- enlever tous les textes de la barre, qui répètent de toute façon ce qui est
  juste au-dessus ;
- mettre la valeur dépouillée au-dessus, en plus petit et en gris ;
- remplacer « accepté » / « refusé » sous le grand chiffre par « extrapolé », et
  mettre « dépouillé » sous le chiffre gris.

**Ce qu'on a fait.**

- *La barre n'a plus aucun texte* : ni mots, ni chiffres. Il reste le rail
  teinté, la moustache et, hors de l'intervalle, le trait gris et sa flèche.
  Elle passe de 62 à 25 px de haut, et tout le code de placement des étiquettes
  disparaît de D′. Un `aria-label` sur la barre garde ses valeurs pour les
  lecteurs d'écran.
- *Deux valeurs côte à côte sous le nom de l'objet*, alignées par le bas :
  l'extrapolé en grand dans la couleur du verdict, libellé « extrapolé » dessous
  dans la même couleur ; le dépouillé en plus petit et en gris, libellé
  « dépouillé » dessous. Les libellés reprennent la typographie de l'ancienne
  pastille (capitales espacées, gras), sans le fond coloré.
- *La pastille accepté / refusé disparaît.* Le verdict se lit dans la couleur
  du chiffre, dans le chiffre lui-même, et dans la barre.
- *Le dépouillé est toujours affiché au-dessus*, qu'il soit dans l'intervalle ou
  non : la règle « seulement dehors » ne vaut que pour la barre.

**Un accroc réglé en route.** Sur trois colonnes, un panneau est plus étroit
qu'un téléphone par rapport au grand chiffre, qui était dimensionné sur la
largeur de l'écran : le dépouillé passait sous l'extrapolé dans un panneau sur
trois à 1240 px, et dans tous à 1000 px. Les deux chiffres sont maintenant
dimensionnés sur la largeur du *panneau* (requêtes de conteneur, unités `cqi`),
avec l'ancienne taille en repli pour les navigateurs qui ne les connaissent
pas. Vérifié à 375, 700, 1000 et 1240 px : côte à côte dans tous les panneaux.
Le grand chiffre passe de 74 à 65 px sur grand écran pour laisser la place.

**Ouvert.** Rien de bloquant. La marge réelle reste une demande à la voie Moteur.

## 2026-09-11, nuit — La barre est finale, et elle entre dans D′

**Décision.** La barre de `barres-proposition.html`, dans son état du commit
précédent, est **la version finale**. Elle est reportée dans D′ à la place de
la piste. Toute évolution de la barre se fait désormais dans D′ ; la planche
reste comme référence, avec ses cinq scénarios et son curseur.

**La barre finale, en résumé.**

- *Intervalle de confiance de l'extrapolation* : une moustache, trait de 3 px
  et deux taquets, dans la couleur du verdict. Pas de pastille.
- *Majorité* : le rail change de teinte à 50, rouge pâle à gauche, bleu pâle à
  droite. Aucune ligne.
- *Dépouillé* : un trait gris, avec une flèche grise vers le bord de
  l'intervalle, **seulement s'il est hors de l'intervalle**. Dedans, rien.
- *Couleurs* : le gris dit ce qu'on a compté (trait, flèche, mot, chiffre du
  dépouillé), la couleur du verdict ce qu'on estime (moustache, mot et chiffre
  de l'extrapolation).
- *Étiquettes* : les mots « extrapolation » et « dépouillé » en petit au-dessus,
  les pourcentages en dessous, centrés sur leur marque. S'ils se chevauchent,
  chacun s'aligne du côté opposé à l'autre ; s'ils se touchent encore, le
  dépouillé perd son mot et son chiffre. Mesuré dans la page.

**Ce qu'on a fait dans D′.**

- La piste (barre pleine jusqu'au projeté, trait à 50) et la ligne « projeté ·
  dépouillé : 54,4 % » sont remplacées par la barre finale.
- *Les marges sont inventées*, les mêmes que la planche par défaut
  (± 2,1, ± 3, ± 4,2 pour LTr, LSU, LPP), dans une constante `MARGES` commentée ;
  le pied de page dit « intervalles de confiance illustratifs ».
- *Les classes sont préfixées `.barre`* pour ne pas heurter celles de D′
  (`.chiffre` y est le grand pourcentage, `.carte` la carte, `.rail` la jauge
  d'avancement).
- *Le placement se recalcule sans redessiner les cartes* : un
  `ResizeObserver` sur le mur replace les étiquettes quand sa largeur change,
  y compris quand la barre de défilement apparaît.

**Ce qu'on a vu.** Sur grand écran (barres de 341 px) comme sur téléphone
(285 px), les trois objets gardent leurs deux chiffres, écartés ; ni
chevauchement ni débordement, aucune erreur. Le grand pourcentage du panneau
et le chiffre de l'extrapolation sous la barre disent la même chose : c'est
voulu par la barre finale, mais c'est un doublon dans D′.

**Ouvert.**

- Le doublon : garder le chiffre de l'extrapolation sous la barre, ou le
  laisser au grand pourcentage du panneau.
- La marge réelle : une demande à la voie Moteur, un champ par objet dans le
  contrat de vue, et `tests/test_contrat.py` qui suit.

## 2026-09-11, soir, suite — Le dépouillé seulement dehors, deux familles de couleur

**Point de départ.** Trois décisions :

- on laisse tomber d'afficher le dépouillé quand il est dans l'intervalle de
  confiance ; on ne le met que quand il est dehors ;
- le trait du dépouillé prend la couleur de la flèche, et le mot
  « extrapolation » celle de l'intervalle ;
- on ne garde que la variation V1, les étiquettes qui s'écartent ; la
  proposition précédente et V2 paraissent moins bien.

**Ce qu'on a fait.** `barres-proposition.html` ne contient plus qu'une barre.

- *La règle des 5 points disparaît*, remplacée par une règle simple : dedans,
  le dépouillé n'est pas dessiné du tout — ni trait, ni flèche, ni mot, ni
  chiffre ; dehors, il l'est. La largeur de l'intervalle ne compte plus.
- *Deux familles de couleur.* Le gris de la flèche (`#9d9c96`) dit ce qu'on a
  compté : trait, flèche, et en gris plus soutenu pour rester lisibles le mot
  et le chiffre du dépouillé. La couleur du verdict dit ce qu'on estime :
  moustache, mot « extrapolation » et chiffre.
- *Le placement des étiquettes est celui de V1* : centrées tant qu'elles
  tiennent, écartées chacune du côté opposé à l'autre sinon, et
  l'extrapolation seule si même écartées elles se touchent.
- *Les deux scénarios fictifs restent.* Ils ne servent plus à comparer étroit
  et large, mais montrent que dedans, quelle que soit la largeur, la barre se
  réduit à la moustache et à son chiffre.

**Ce qu'on a vu.** Sur téléphone comme sur grand écran, les trois objets du
jour gardent leurs deux chiffres ; aucun chevauchement ni débordement de la
marge ± 0,5 à ± 8. Le trait gris, moins contrasté que le noir, reste lisible
grâce à son halo blanc et parce qu'il dépasse du rail. La barre est plus calme :
seule la couleur du verdict attire l'œil, et elle est sur ce qui compte.

**Ouvert.** Le report dans D′, à la place de la piste actuelle.

## 2026-09-11, soir — Alléger la barre retenue

**Point de départ.** Quatre retouches sur la barre retenue, et une ou deux
variations si des idées peuvent l'améliorer :

- enlever les « ± » du texte sous la barre, qui alourdissent ;
- mettre les deux pourcentages en bas tant qu'ils ne se chevauchent pas, et
  seulement l'extrapolation s'ils se chevauchent ;
- mettre au-dessus, dans une police discrète, « extrapolation » et
  « dépouillé » ;
- rendre la flèche plus subtile, en gris.

**Ce qu'on a fait.**

- *Sous la barre, rien que des pourcentages.* Les « ± » sont partis, et avec
  eux les mentions « dépouillé dans la marge », qui relevaient du même
  alourdissement. Chaque chiffre est centré sous sa marque : l'extrapolation
  en gras dans la couleur du verdict, le dépouillé en gris.
- *Au-dessus, deux mots* en petit gris, « extrapolation » et « dépouillé »,
  chacun au-dessus de sa marque.
- *Les chevauchements sont mesurés dans la page*, à chaque largeur d'écran,
  avec 8 px de marge. Si les chiffres se chevauchent, le dépouillé perd son
  chiffre *et* son mot. Si seuls les mots se chevauchent — ils sont plus longs
  que les chiffres — mots et chiffres s'alignent chacun du côté opposé à
  l'autre.
- *La flèche est grise* (`#9d9c96`), plus fine, pointe plus petite.
- *Deux variations* : V1, les étiquettes s'écartent avant de disparaître ; V2,
  la flèche en pointillé, sans pointe.

**Ce qu'on a vu.** La règle telle quelle marche sur grand écran : la barre fait
726 px, les trois objets du jour gardent leurs deux chiffres. Sur téléphone,
elle ne marche pas : la barre fait 281 px, deux chiffres centrés y ont besoin
d'une vingtaine de points d'écart, et la proposition perd le chiffre du
dépouillé sur les trois objets. V1, qui écarte les chiffres avant de renoncer,
les garde tous les trois ; dans les cas vraiment serrés (fin, mi-parcours) les
deux donnent la même chose. V2 allège encore, mais le pointillé gris sur le
rail pâle se devine plus qu'il ne se voit.

Au passage : la pointe de flèche restait noire, le raccourci CSS `border-left`
reprenant la couleur du texte ; on lui donne désormais la couleur de la flèche.

**Décision proposée.** Adopter V1 comme règle : elle est la proposition sur
grand écran, et la seule qui tienne sur téléphone.

**Ouvert.** Adopter V1 ou non ; V2 ou la flèche grise ; puis le report dans D′.

## 2026-09-11, fin — La barre retenue

**Point de départ.** Une seule proposition, à partir de C4 (moustaches), avec
le rail teinté de R4 pour la majorité. Et une règle à deux conditions pour le
trait du dépouillé : l'enlever si l'intervalle de confiance est petit, sous
5 points, *et* que le dépouillé tombe dedans. Ajouter un cinquième scénario
pour voir la différence au-dessus et en dessous de 5 points.

**Ce qu'on a fait.** `barres-proposition.html`, une page pour une barre :

- *L'intervalle* est la moustache de C4 — un trait horizontal de 3 px dans la
  couleur du verdict projeté, deux taquets — sans pastille. Le chiffre est le
  projeté.
- *La majorité* est le rail teinté de R4 : rouge pâle à gauche de 50, bleu
  pâle à droite, 9 px de haut, aucune ligne. La question « l'intervalle
  passe-t-il 50 ? » se lit comme « la moustache chevauche-t-elle la
  frontière ? ».
- *Le dépouillé* est le trait noir à halo, avec la flèche vers le bord de
  l'intervalle quand il est dehors. **Règle** : il s'efface si l'intervalle
  fait moins de 5 points de large (bornes comprises : `hi − lo < 5`) *et* que
  le dépouillé est dedans. Sa valeur passe alors dans l'étiquette du projeté,
  « dépouillé 50,7 %, dans la marge ». Dedans mais intervalle large : le trait
  reste, sans flèche.
- *Cinq scénarios* : les trois objets du jour, la fin du dépouillement
  (étroit, dedans, × 0,5 : le trait s'efface) et un mi-parcours fictif à
  47,9 → 48,6 %, × 1,2 (large, dedans : le trait reste). À côté de chaque nom,
  la règle appliquée est écrite : « dedans, intervalle de 7,2 pts ≥ 5 → trait
  gardé ». Au curseur, le mi-parcours bascule entre ± 2 et ± 2,5, la fin entre
  ± 4,5 et ± 5.

**Décisions.**

- *Le seuil est une constante de la page*, `SEUIL = 5`, mesuré en largeur
  totale d'intervalle. Si le site calcule un jour une marge, c'est elle qui le
  fixera — et il faudra dire si 5 points, c'est ± 2,5 ou ± 5.
- *La règle est écrite à côté de chaque barre*, pour la maquette seulement :
  c'est un outil de discussion, pas un élément du site.
- *La flèche reste noire*, comme le trait : les faits en encre, le verdict en
  couleur sur la moustache. Le rail ne porte que la teinte du côté.

**Ce qu'on a vu.** Sur le rail teinté, la moustache colorée se lit bien, y
compris quand elle chevauche la frontière — un trait bleu qui mord dans le
rose dit « en jeu » sans mot. Quand le trait s'efface, la barre devient très
calme : une moustache courte, un chiffre. C'est l'état de fin de soirée, et
c'est ce qu'on voulait.

**Ouvert.** Reporter cette barre dans D′, à la place de la piste actuelle —
et poser à la voie Moteur la question de la marge, dont dépend désormais la
règle d'affichage.

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
