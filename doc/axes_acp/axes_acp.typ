// Que mesurent les axes de l'ACP ? — document public, doc/axes_acp.pdf.
// Les chiffres des tableaux viennent de resultats.json (analyse.py) ; le texte
// est rédigé d'après ces mêmes chiffres, calculés le 18.09.2026. Rien de
// technique ici (ni code, ni fichier) : le détail est dans README.md.

#import "fiches.typ": fiches
#let R = json("resultats.json")

// ─── Charte ────────────────────────────────────────────────────────────────
#let BLEU = rgb("#2a78d6")
#let ROUGE = rgb("#c9352b")
#let ENCRE = rgb("#1f1f1c")
#let ENCRE2 = rgb("#52514e")
#let MUET = rgb("#898781")
#let GRILLE = rgb("#e1e0d9")
#let FOND = rgb("#f5f4f0")
#let SERIES = (rgb("#2a78d6"), rgb("#eb6834"), rgb("#1baf7a"))

#set document(title: "Que mesurent les axes de l'ACP ?", author: "Politiques.ch")
#set page(
  paper: "a4",
  margin: (x: 2cm, top: 2.1cm, bottom: 2cm),
  header: context {
    if counter(page).get().first() > 1 {
      set text(7.5pt, fill: MUET)
      [Que mesurent les axes de l'ACP ? #h(1fr) Politiques.ch · septembre 2026]
    }
  },
  footer: context {
    set text(7.5pt, fill: MUET)
    h(1fr)
    counter(page).display()
  },
)
#set text(font: ("Helvetica Neue", "Helvetica", "Arial"), size: 9.5pt, lang: "fr", region: "ch", fill: ENCRE)
#set par(justify: true, leading: 0.6em, spacing: 0.95em)
#set heading(numbering: "1.1")
#show heading.where(level: 1): it => {
  v(0.9em)
  text(15pt, weight: "bold", it)
  v(0.4em)
}
#show heading.where(level: 2): it => {
  v(0.5em)
  text(11pt, weight: "bold", it)
  v(0.15em)
}
#show heading.where(level: 3): it => {
  v(0.3em)
  text(9.5pt, weight: "bold", it)
}
#set table(stroke: none, inset: (x: 3.5pt, y: 2.6pt), align: (x, y) => (if x == 0 { left } else { right }) + horizon)
#show table: set text(7.8pt)
#show table: set par(justify: false)
#show figure.caption: set text(8pt, fill: ENCRE2)
#show figure.caption: set par(justify: false)
#show figure.caption: set align(left)
#set figure(gap: 0.55em)
#set list(indent: 0.4em, spacing: 0.7em)

// ─── Outils ────────────────────────────────────────────────────────────────

// Nombre à la française : virgule décimale, vrai signe moins, décimales fixes.
#let num(x, d: 2) = {
  if x == none { return "—" }
  let s = str(calc.round(calc.abs(x), digits: d))
  let parties = s.split(".")
  let dec = if parties.len() > 1 { parties.at(1) } else { "" }
  while dec.len() < d { dec += "0" }
  let t = if d > 0 { parties.at(0) + "," + dec } else { parties.at(0) }
  let nul = t.replace("0", "").replace(",", "") == ""
  if x < 0 and not nul { "−" + t } else { t }
}
#let pc(x, d: 1) = num(x * 100, d: d) + "\u{00A0}%"
#let sg(x, d: 2) = if x != none and x > 0 { "+" + num(x, d: d) } else { num(x, d: d) }

// Fond d'une case selon une corrélation : bleu si positive, rouge si négative.
#let teinte(v, force: 55%) = {
  if v == none { return none }
  let a = calc.min(calc.abs(v), 1)
  let c = if v >= 0 { BLEU } else { ROUGE }
  c.transparentize(100% - a * force)
}
#let cc(v, d: 2, force: 55%) = table.cell(fill: teinte(v, force: force))[#num(v, d: d)]
// Même chose, avec une teinte mise à l'échelle : on affiche v, on colore v / echelle.
#let cce(v, echelle, d: 2) = table.cell(fill: teinte(v / echelle))[#num(v, d: d)]
#let r2c(v) = table.cell(fill: BLEU.transparentize(100% - calc.max(v, 0) * 60%))[#num(v, d: 2)]

#let filet = table.hline(stroke: 0.5pt + GRILLE)
#let entete(..cellules) = cellules.pos().map(c => text(weight: "bold", c))

// Mot d'ordre : oui en bleu, non en rouge, comme les cartes.
#let parole(v) = {
  if v == none { text(fill: MUET, "·") }
  else if v == 1 { text(fill: BLEU, weight: "bold", "oui") }
  else if v == -1 { text(fill: ROUGE, weight: "bold", "non") }
  else { text(fill: ENCRE2, "lib.") }
}

#let O = {
  let d = (:)
  for o in R.objets { d.insert(str(o.sujet_id), o) }
  d
}
#let annee(o) = o.date.slice(0, 4)
#let date_fr(o) = {
  let (a, m, j) = o.date.split("-")
  j + "." + m + "." + a
}
#let CANTON_NOM = (
  ZH: "Zurich", BE: "Berne", LU: "Lucerne", UR: "Uri", SZ: "Schwyz", OW: "Obwald",
  NW: "Nidwald", GL: "Glaris", ZG: "Zoug", FR: "Fribourg", SO: "Soleure",
  BS: "Bâle-Ville", BL: "Bâle-Campagne", SH: "Schaffhouse", AR: "Appenzell RE",
  AI: "Appenzell RI", SG: "Saint-Gall", GR: "Grisons", AG: "Argovie", TG: "Thurgovie",
  TI: "Tessin", VD: "Vaud", VS: "Valais", NE: "Neuchâtel", GE: "Genève", JU: "Jura",
)
#let DIMENSION = ("gauche–droite", "ouverture–souverainisme", "écologie–bloc bourgeois")
#let DIM_COURT = ("F1", "F2", "F3")

// Deux listes côte à côte : les objets les plus liés à chaque pôle d'un axe.
#let poles(bas, haut, k, titre_bas, titre_haut, n: 8, facteur: false) = {
  let ligne(id) = {
    let o = O.at(str(id))
    let v = if facteur { o.facteurs.at(k) } else { o.axes.at(k) }
    (o.etiquette + " (" + annee(o) + ")", cc(v), [#pc(o.oui, d: 0)])
  }
  grid(columns: (1fr, 1fr), column-gutter: 10pt,
    table(columns: (1fr, auto, auto),
      ..entete(text(fill: ROUGE, titre_bas), "corr.", "oui"), filet,
      ..bas.slice(0, n).map(ligne).flatten()),
    table(columns: (1fr, auto, auto),
      ..entete(text(fill: BLEU, titre_haut), "corr.", "oui"), filet,
      ..haut.slice(0, n).map(ligne).flatten()),
  )
}

#let communes_extremes(c) = {
  let f(l) = l.map(x => x.nom.replace(regex(" \(([A-Z]{2})\)$"), "") + " (" + x.canton + ")").join(", ")
  [#text(fill: ROUGE)[Côté négatif :] #f(c.bas). #text(fill: BLEU)[Côté positif :] #f(c.haut).]
}

#let encadre(corps) = block(fill: FOND, inset: 8pt, radius: 2pt, width: 100%, corps)

// ════════════════════════════════════════════════════════════════════════════
// Titre et résumé
// ════════════════════════════════════════════════════════════════════════════

#block(width: 100%)[
  #text(8pt, fill: MUET)[POLITIQUES.CH · SEPTEMBRE 2026]
  #v(0.3em)
  #text(21pt, weight: "bold")[Que mesurent les axes de l'ACP ?]
  #v(0.1em)
  #text(11pt, fill: ENCRE2)[Lecture politique des six axes qui résument le vote des communes suisses, et classification des #R.meta.objets objets fédéraux votés du 30 novembre 2014 au 14 juin 2026]
  #v(0.2em)
  #text(8pt, fill: MUET)[Résultats communaux : Office fédéral de la statistique · mots d'ordre : Swissvotes (Université de Berne) · force des partis : OFS]
]
#v(0.6em)

#heading(level: 2, numbering: none)[En bref]

- *Les trois premiers axes (#pc(R.variance.at(0) + R.variance.at(1) + R.variance.at(2), d: 0) des différences entre communes) dessinent un triangle.* Ses sommets sont les trois camps de la politique suisse : la gauche (PS, Verts, syndicats), la droite nationale-conservatrice (UDC) et le centre-droit gouvernemental (PLR, Centre, PVL, avec le Conseil fédéral et economiesuisse).
- *Axe 1 (#pc(R.variance.at(0))) : l'UDC contre la gauche.* Le Conseil fédéral, le PLR et le Centre sont au milieu. C'est le gauche–droite tel qu'il se vote en Suisse : il mêle question sociale et question identitaire, et il porte aussi le Röstigraben, la Romandie votant à gauche.
- *Axe 2 (#pc(R.variance.at(1))) : le camp gouvernemental contre la contestation, qu'elle vienne de gauche ou de droite.* D'un côté le PLR, le Centre, le PVL et le Conseil fédéral ; l'UDC et le PS sont au milieu ; de l'autre, des initiatives qui prospèrent en périphérie, surtout latine (argent liquide, primes, liberté vaccinale). L'axe s'est renforcé depuis 2020.
- *Axe 3 (#pc(R.variance.at(2))) : la gauche écologiste des villes alémaniques contre le bloc bourgeois uni*, UDC et paysans compris : pesticides et forfaits fiscaux d'un côté, RIE III et routes de l'autre.
- *Vus sous un autre angle (une rotation de #num(R.angle_rotation, d: 1)°), les axes 1 et 2 font apparaître deux dimensions classiques bien séparées.* La première est le gauche–droite de l'État social, qui suit la frontière des langues. La seconde oppose l'ouverture au souverainisme, avec l'UDC seule contre tous, et suit l'opposition ville–campagne. Avec l'axe 3, on retrouve les trois dimensions que Hermann et Leuthold avaient tirées des votes de 1982-2002.
- *Les axes 4 à 6 (environ 3 % chacun) sont régionaux et moins stables :*
  - un axe confessionnel : le Haut-Valais, le Tessin et les Grisons catholiques contre le Vaud protestant ;
  - un axe Tessin contre Grisons ;
  - un axe fragile, qui oppose le Mittelland industriel à la montagne paysanne.

#v(0.3em)
#figure(
  table(
    columns: (auto, auto, 1fr, 1fr, auto, auto),
    align: left + horizon,
    ..entete("Axe", "Poids", text(fill: ROUGE)[Côté négatif (rouge)], text(fill: BLEU)[Côté positif (bleu)], "En bref", "Stabilité"),
    filet,
    [1], [#pc(R.variance.at(0))], [UDC, souverainisme, conservatisme], [gauche, ouverture, Romandie], [Gauche – UDC], [très stable],
    [2], [#pc(R.variance.at(1))], [camp gouvernemental, communes aisées], [contestation, périphérie latine], [Contestation – gouvernement], [stable depuis 2020],
    [3], [#pc(R.variance.at(2))], [bloc bourgeois, montagne et tourisme], [écologie des villes alémaniques], [Écologie – bloc bourgeois], [stable avec l'axe 2],
    [4], [#pc(R.variance.at(3))], [protestant (Vaud)], [catholique (Haut-Valais, Tessin)], [Catholique – protestant], [se mêle à l'axe 5],
    [5], [#pc(R.variance.at(4))], [Tessin], [Grisons, montagne], [Grisons – Tessin], [se mêle à l'axe 4],
    [6], [#pc(R.variance.at(5))], [Mittelland industriel], [montagne paysanne], [—], [fragile],
  ),
  caption: [Les six axes et la lecture que ce document en propose. Poids : part des différences entre communes que l'axe résume. Bleu du côté positif, rouge du côté négatif, comme sur les cartes du site.],
)

#encadre[*Des axes qui vivent.* Les axes sont recalculés après chaque votation fédérale. Un nouvel objet les déplace à peine (celui du 14 juin 2026 ne les a pas changés, § 6), mais leur sens peut évoluer au fil des années. Ce document décrit les axes de septembre 2026.]

#pagebreak()
#outline(title: [Sommaire], depth: 1, indent: 1em)

// ════════════════════════════════════════════════════════════════════════════
= L'ACP, base de nos analyses
// ════════════════════════════════════════════════════════════════════════════

== Ce qu'est une ACP

Chaque commune suisse a voté sur les mêmes objets fédéraux. Depuis novembre 2014, cela fait #R.meta.objets votes, donc #R.meta.objets pourcentages de oui par commune. Comparer deux communes sur #R.meta.objets chiffres à la fois, c'est illisible. Mais ces chiffres ne sont pas indépendants : une commune qui a dit oui au congé paternité a très probablement dit non à la limitation de l'immigration. Les votes suivent quelques grandes lignes de partage, toujours les mêmes.

L'*analyse en composantes principales* (ACP) cherche ces lignes de partage dans les chiffres, sans rien savoir des partis ni des thèmes. Elle trouve d'abord la direction qui résume le plus de différences entre communes : c'est l'*axe 1*. Elle cherche ensuite, parmi ce qui reste, la direction suivante : c'est l'*axe 2*, et ainsi de suite. Chaque commune reçoit une position sur chaque axe. Deux communes proches sur les premiers axes votent presque toujours de la même manière.

L'ACP dit _combien_ chaque axe compte, pas _ce qu'il signifie_. Nommer les axes est un travail d'interprétation : c'est l'objet de ce document.

#figure(image("figures/eboulis.pdf", width: 88%),
  caption: [Part des différences entre communes que résume chaque axe. Les trois premiers en concentrent #pc(R.variance.at(0) + R.variance.at(1) + R.variance.at(2), d: 0), les trois suivants #pc(R.variance.at(3) + R.variance.at(4) + R.variance.at(5), d: 0) à eux trois ; au-delà, chaque axe pèse moins de 1,5 %.])

== À quoi elle sert sur Politiques.ch

Toutes nos analyses reposent sur ces six premiers axes.

- *Les projections des soirs de votation.* Les premières communes dépouillées ne ressemblent pas à la Suisse : ce sont surtout des petites communes rurales. Leur profil sur les axes permet de corriger ce biais. On regarde comment le vote du jour dépend de la position des communes déjà connues, et on en déduit le vote des communes qui ne le sont pas encore.
- *Les pages « Communes » et « Objets de votation ».* Elles montrent les communes et les objets dans le plan de deux axes, et les cartes qui vont avec.

== Les données

- *Les communes.* #R.meta.communes_suisses communes, plus 12 circonscriptions de Suisses de l'étranger, soit #R.meta.communes unités ayant voté sur tous les objets. Chacune compte pour une, quelle que soit sa taille.
- *Les objets.* Les #R.meta.objets objets fédéraux votés du 30 novembre 2014 au 14 juin 2026, avec leurs résultats communaux officiels (Office fédéral de la statistique).
- *Les mots d'ordre.* Pour chaque objet, la position du Conseil fédéral et du Parlement et les mots d'ordre des partis, des grandes associations et des sections cantonales dissidentes, tirés de Swissvotes, la base de données des votations fédérales de l'Université de Berne.
- *La force des partis* aux élections au Conseil national de 2023, commune par commune (OFS).
- *La langue et le degré d'urbanisation* des communes (OFS).
- *Les enjeux des objets*, résumés pour ce document (annexe B).

== Comment lire un axe

On lit un axe par la corrélation de chaque objet avec lui, comme sur la page « Objets de votation » du site. Une corrélation positive veut dire que les communes du côté positif de l'axe ont voté oui plus souvent que les autres. Le côté où tombe un objet dit donc où se trouvent ses partisans, pas s'il est « de gauche » ou « de droite ». Une initiative de gauche et une réforme de droite combattue par la gauche tombent du même côté : dans les deux cas, ce sont les communes de gauche qui ont voté comme la gauche le demandait.

Le sens d'un axe est arbitraire : le côté « positif » n'est pas meilleur que l'autre. Ce document garde celui du site, bleu pour le côté positif et rouge pour le côté négatif, comme sur les cartes.

== Quatre outils d'interprétation

+ *Les acteurs comme des communes fictives.* Un parti qui recommande le oui est traité comme une commune qui voterait oui à 100 %, un parti qui recommande le non comme une commune à 0 %, la liberté de vote comme 50 %. On le place ensuite sur les axes comme les vraies communes. On fait de même pour le Conseil fédéral et les grandes associations.
+ *Les mots d'ordre comme explication des objets.* On mesure dans quelle proportion les mots d'ordre d'un parti expliquent la place des objets sur un axe. C'est le R², qui va de 0 (rien) à 1 (tout).
+ *Les communes.* On confronte leur position à la langue, au degré d'urbanisation, à la taille et à la force des partis. On calcule aussi, pour chaque commune, un _indice de suivi_ : la part moyenne des votants qui ont voté comme un acteur le recommandait.
+ *La rotation.* On fait tourner les premiers axes pour que chaque objet se rattache le plus possible à un seul d'entre eux (méthode « varimax »). La rotation ne change pas l'information, seulement la lecture (§ 4).

// ════════════════════════════════════════════════════════════════════════════
= Vue d'ensemble : un triangle à trois pôles
// ════════════════════════════════════════════════════════════════════════════

#figure(image("figures/partis_plan12.pdf", width: 94%),
  caption: [Plan des axes 1 et 2. Points de couleur : les communes, selon leur langue. En noir : les acteurs placés comme des communes fictives (§ 1.5), en gras les grands partis et le Conseil fédéral. Tirets : les deux facteurs de la rotation (§ 4).])

Projetés dans le plan des deux premiers axes, les acteurs forment un triangle. L'UDC et l'UDF sont à gauche du graphique ; le PS, les Verts et les syndicats à droite ; le PLR, le Centre, le PVL, le Conseil fédéral et economiesuisse en bas. L'axe 1 sépare l'UDC de la gauche et laisse le camp gouvernemental au milieu. L'axe 2 isole le camp gouvernemental des deux autres pôles, qui s'y retrouvent à égalité. Personne ne tient le haut du graphique : aucun grand parti ne recommande régulièrement ce que votent les communes de ce côté. Seuls de petits partis s'en approchent (PST-POP, MCG, Lega, UDF).

Les communes, elles, s'étirent surtout le long de l'axe 1. La Suisse alémanique en occupe le côté négatif, la Romandie le côté positif, et le Tessin se tient entre les deux, un peu plus haut.

#figure(
  table(
    columns: (1.6fr, ..range(6).map(_ => 1fr), 0.2fr, ..range(3).map(_ => 1fr)),
    ..entete("Acteur", "Axe 1", "Axe 2", "Axe 3", "Axe 4", "Axe 5", "Axe 6", "", "F1", "F2", "F3"),
    filet,
    ..("CF", "UDC", "PLR", "Centre", "PVL", "PS", "Verts", "PEV", "UDF", "Lega", "MCG", "PST", "economiesuisse", "USAM", "USP", "USS", "TravS", "Villes", "Cantons").map(a => {
      let x = R.acteurs.at(a)
      (x.libelle, ..x.alignement.map(v => cc(v)), [], ..x.position_rot.map(v => cce(v, 8, d: 1)))
    }).flatten(),
  ),
  caption: [Axes 1 à 6 : indice d'alignement de chaque acteur, c'est-à-dire la corrélation entre ses mots d'ordre (oui = +1, non = −1) et la corrélation des objets avec l'axe. +1 veut dire qu'il recommande toujours le oui aux objets du côté positif et le non à ceux du côté négatif. F1 à F3 : position de l'acteur, projeté comme commune fictive, sur les facteurs tournés (§ 4), en écarts-types des communes.],
)

#figure(
  table(
    columns: (2.4fr, ..range(6).map(_ => 1fr)),
    ..entete("Variables explicatives", "Axe 1", "Axe 2", "Axe 3", "Axe 4", "Axe 5", "Axe 6"),
    filet,
    ..R.r2_objets.pairs().map(((nom, v)) => (nom, ..v.map(r2c))).flatten(),
  ),
  caption: [Part de la place des #R.meta.objets objets sur chaque axe (R², de 0 à 1) qu'expliquent les mots d'ordre, le fait d'être une initiative ou le domaine politique (Swissvotes).],
)

Ces mesures précisent le triangle.

- *Axe 1.* Les mots d'ordre du PS expliquent à eux seuls #pc(R.r2_objets.at("Mot d'ordre PS").at(0), d: 0) de la position des objets, ceux de l'UDC #pc(R.r2_objets.at("Mot d'ordre UDC").at(0), d: 0), la position du Conseil fédéral #pc(R.r2_objets.at("Position du Conseil fédéral").at(0), d: 0) seulement.
- *Axe 2.* C'est l'inverse : le Conseil fédéral (#pc(R.r2_objets.at("Position du Conseil fédéral").at(1), d: 0)), le PLR (#pc(R.r2_objets.at("Mot d'ordre PLR").at(1), d: 0)) et le simple fait d'être une initiative populaire (#pc(R.r2_objets.at("Initiative (ou non)").at(1), d: 0)).
- *Axe 3.* Aucun acteur ne domine. Le Conseil fédéral, l'initiative, l'UDC, le PLR et l'Union suisse des paysans y contribuent chacun pour environ un tiers.
- *Au-delà de l'axe 3.* Les mots d'ordre n'expliquent presque plus rien : ces axes-là ne sont pas partisans.

#figure(
  table(
    columns: (2.2fr, auto, auto, 1fr, 1fr, 1fr, 0.2fr, 1fr, 1fr, 1fr),
    ..entete("Configuration des mots d'ordre", "Objets", "Initiatives", "Axe 1", "Axe 2", "Axe 3", "", "F1", "F2", "F3"),
    filet,
    ..R.motifs.map(m => (m.motif, str(m.n), pc(m.initiatives, d: 0), ..m.axes.map(r2c), [], ..m.facteurs.map(r2c))).flatten(),
  ),
  caption: [Configuration des mots d'ordre des six grands partis face au Conseil fédéral, et part de variance moyenne (corrélation au carré) des objets de chaque groupe sur les axes et les facteurs tournés. « UDC seule contre » : l'UDC recommandait le contraire du Conseil fédéral, les cinq autres grands partis le suivaient.],
)

Les configurations de mots d'ordre donnent la même image. Quand l'UDC est seule contre tous, l'objet se range sur l'axe 1 et, après rotation, sur le facteur ouverture–souverainisme. Quand la gauche est seule contre, il se range aussi sur l'axe 1, mais sur le facteur gauche–droite. L'axe 1 réunit donc les deux grandes oppositions de la politique suisse ; la rotation les sépare (§ 4).

// ════════════════════════════════════════════════════════════════════════════
= Les axes un par un
// ════════════════════════════════════════════════════════════════════════════

#let bloc_communes(k) = {
  let a = R.axes.at(k)
  let l = a.langue
  let u = a.urbanisation
  table(
    columns: (auto, ..range(7).map(_ => 1fr)),
    ..entete("Moyenne des communes", "allemand", "français", "italien", "romanche", "urbain", "intermédiaire", "rural"),
    filet,
    [Axe #(k + 1) (en écarts-types)],
    ..("allemand", "français", "italien", "romanche").map(x => cc(l.at(x) / a.ecart_type)),
    ..("urbain", "intermédiaire", "rural").map(x => cc(u.at(x) / a.ecart_type)),
  )
}

#let force_axe(k) = {
  let partis = ("UDC", "PLR", "Centre", "PVL", "PS", "Verts", "Lega")
  table(
    columns: (auto, ..partis.map(_ => 1fr)),
    ..entete("Corrélation avec la force du parti (2023)", ..partis),
    filet,
    [Axe #(k + 1)], ..partis.map(p => cc(R.force_partis.at(p).axes.at(k))),
  )
}

== Axe 1 (#pc(R.variance.at(0))) : l'UDC contre la gauche

#poles(R.axes.at(0).objets_bas, R.axes.at(0).objets_haut, 0, "Côté négatif", "Côté positif")

*Ce qui est en jeu.* Côté négatif : l'immigration et la souveraineté (« 10 millions », limitation, renvoi, autodétermination), l'armée (avions de combat, service civil) et le contrôle social (surveillance des assurés). Côté positif : les réformes de société (congé paternité, norme contre l'homophobie, naturalisation facilitée), la culture, le climat et l'agriculture écologique. Les objets les plus nets sont presque tous ceux où l'UDC était seule contre tous, ou seule avec une partie du PLR.

*Qui soutient quoi.* L'UDC et l'UDF d'un côté (alignement #num(R.acteurs.UDC.alignement.at(0))), le PS, les Verts et les syndicats de l'autre (#num(R.acteurs.PS.alignement.at(0)) pour le PS). Le Conseil fédéral, le Centre et le PLR se tiennent près de zéro, le PVL un peu du côté de la gauche.

*Où.* L'axe 1 est presque exactement l'indice de suivi du PS (r = #num(R.suivi.PS.axes.at(0))) ou, au signe près, celui de l'UDC (r = #num(R.suivi.UDC.axes.at(0))). La force des partis en 2023 explique #pc(R.r2_communes.at("Force des partis (2023)").at(0), d: 0) de la position des communes, et la langue à elle seule #pc(R.r2_communes.at("Langue").at(0), d: 0). #communes_extremes(R.axes.at(0).communes)

#bloc_communes(0)
#force_axe(0)

#figure(image("figures/carte_axe1.png", width: 92%), caption: [Axe 1 sur la carte des communes. Les communes des Suisses de l'étranger n'ont pas de contour.])

#block(breakable: false)[*Lectures possibles.*
- *Partisane : « gauche – UDC ».* C'est la plus exacte, parce que l'axe se confond avec les indices de suivi du PS et de l'UDC.
- *Classique : « progressiste – conservateur » ou « ouverture – fermeture ».* Elle convient aux objets de société et d'identité, moins bien aux retraites.
- *Sociogéographique : « Romandie et villes contre Suisse centrale et alémanique rurale ».*
]

Aucune ne rend compte seule de l'axe, qui mélange deux dimensions distinctes (§ 4).

== Axe 2 (#pc(R.variance.at(1))) : le camp gouvernemental contre la contestation

#poles(R.axes.at(1).objets_bas, R.axes.at(1).objets_haut, 1, "Côté négatif", "Côté positif")

*Ce qui est en jeu.* Côté négatif, des objets que le Conseil fédéral, le Parlement et les partis gouvernementaux défendaient ensemble : AVS 21 et son financement par la TVA, l'impôt anticipé, la loi COVID, l'e-ID, l'accord avec l'Indonésie, EFAS. Côté positif, des initiatives que ce camp combattait et qui ont trouvé des voix des deux bords :
- l'argent liquide et la « liberté et intégrité physique », venues des milieux opposés aux mesures sanitaires ;
- la burqa, venue de la droite ;
- les primes, la 13#super[e] rente et le service public, venus de la gauche ou des consommateurs.

*Qui soutient quoi.* Le PLR (alignement #num(R.acteurs.PLR.alignement.at(1))), le Conseil fédéral (#num(R.acteurs.CF.alignement.at(1))), economiesuisse, le Centre et le PVL tiennent le côté négatif. L'UDC (#num(R.acteurs.UDC.alignement.at(1))) et le PS (#num(R.acteurs.PS.alignement.at(1))) sont neutres. Seuls de petits partis penchent du côté positif (PST-POP, MCG, UDF). L'axe oppose donc le camp gouvernemental au reste du pays plutôt qu'un parti à un autre.

*Où.* Le côté négatif, ce sont les communes aisées qui suivent les recommandations des autorités, avec des indices de suivi de r = #num(R.suivi.PLR.axes.at(1)) pour le PLR, #num(R.suivi.economiesuisse.axes.at(1)) pour economiesuisse et #num(R.suivi.CF.axes.at(1)) pour le Conseil fédéral. Le côté positif, ce sont les communes rurales de la périphérie, surtout latines : Jura, Jura bernois, Broye fribourgeoise, Tessin. #communes_extremes(R.axes.at(1).communes)

#bloc_communes(1)
#force_axe(1)

#figure(image("figures/carte_axe2.png", width: 92%), caption: [Axe 2 sur la carte des communes.])

*Un axe qui s'est renforcé.* Sur les seuls objets de 2020 à 2026, le deuxième axe pèse #pc(R.robustesse.periodes.at("2020-2026").variance.at(1)) de la variance, contre #pc(R.robustesse.periodes.at("2014-2019").variance.at(1)) sur ceux de 2014 à 2019. Avant 2020, il se mêlait à l'axe 3 (§ 6). Les trois référendums COVID, l'e-ID, l'argent liquide et la liberté vaccinale lui ont donné sa forme actuelle.

#block(breakable: false)[*Lectures possibles.*
- *« Camp gouvernemental – contestation »*, ou confiance contre défiance envers les autorités. C'est la plus fidèle aux mots d'ordre.
- *« Droite économique aisée – périphérie sociale et souverainiste ».* C'est la plus fidèle à la carte.
- *Géométrique.* L'axe 2 est la différence entre les deux dimensions classiques : il oppose la « droite ouverte » à la « gauche souverainiste » (§ 4). Ces trois lectures décrivent la même chose.
]

== Axe 3 (#pc(R.variance.at(2))) : la gauche écologiste des villes contre le bloc bourgeois

#poles(R.axes.at(2).objets_bas, R.axes.at(2).objets_haut, 2, "Côté négatif", "Côté positif")

*Ce qui est en jeu.* Côté négatif, la fiscalité des entreprises (RIE III, RFFA, droits de timbre, impôt anticipé), les routes (FORTA), le renseignement et la chasse au loup. Côté positif, l'agriculture écologique (eau potable, pesticides, élevage intensif), la protection du territoire (biodiversité, mitage) et l'imposition des riches (forfaits fiscaux, successions), plus quelques initiatives citoyennes sans parti (juges tirés au sort).

*Qui soutient quoi.* Les Verts, le PS, le PST-POP et le PEV d'un côté. De l'autre, un bloc bourgeois où l'UDC se range avec le PLR, le Centre et le Conseil fédéral. L'Union suisse des paysans y est alignée plus que partout ailleurs (#num(R.acteurs.USP.alignement.at(2))). Les partis expliquent pourtant mal les communes : la force des partis en 2023 n'en explique que #pc(R.r2_communes.at("Force des partis (2023)").at(2), d: 0).

*Où.* Les villes alémaniques d'un côté (Berne, Bienne, Zurich, Bâle, Winterthour), avec des communes « alternatives » comme Trogen ou Rodersdorf. De l'autre, les stations touristiques et la montagne (Ormont-Dessus, Saas-Fee, Château-d'Oex, Flühli), et plus largement la Romandie et le Valais. #communes_extremes(R.axes.at(2).communes)

#bloc_communes(2)
#force_axe(2)

#figure(image("figures/carte_axe3.png", width: 92%), caption: [Axe 3 sur la carte des communes.])

#block(breakable: false)[*Lectures possibles.*
- *« Écologique – technocratique ».* C'est la troisième dimension de Hermann et Leuthold, où l'environnement et les transports opposaient l'écologie à la croissance.
- *« Post-matérialisme urbain alémanique – bloc bourgeois et paysan ».*
- *« Imposer les riches – alléger les entreprises ».*
]

Les trois lectures désignent le même électorat : une gauche urbaine alémanique qui vote plus à gauche que la Romandie sur l'écologie et la fiscalité, alors que c'est l'inverse sur les retraites et la santé.

== Axes 4 à 6 : trois axes régionaux

#grid(columns: (1fr, 1fr, 1fr), column-gutter: 6pt,
  figure(image("figures/carte_axe4.png", width: 100%), caption: [Axe 4]),
  figure(image("figures/carte_axe5.png", width: 100%), caption: [Axe 5]),
  figure(image("figures/carte_axe6.png", width: 100%), caption: [Axe 6]),
)

*Axe 4 (#pc(R.variance.at(3))) : catholique contre protestant.* Côté positif, le Haut-Valais catholique (Saas-Fee, Visperterminen, Rarogne), le Val d'Hérens, les vallées grisonnes et le Tessin. Côté négatif, le Vaud protestant (Servion, Sainte-Croix, le Jorat). L'axe suit la force du Centre, l'ancien PDC (r = #num(R.force_partis.Centre.axes.at(3))), et s'oppose à celle de l'UDC (#num(R.force_partis.UDC.axes.at(3))).

Ses objets positifs sont des projets du PDC ou chers à lui : le frein aux coûts de la santé, les allocations familiales exonérées, Prévoyance 2020. Ses objets négatifs sont ceux où les communes catholiques ont moins voté oui que leur profil ne le laissait attendre : le diagnostic préimplantatoire, le mariage pour tous, l'imposition individuelle. C'est le vieux clivage confessionnel, que les partis nationaux ne portent plus mais que les votes gardent.

#poles(R.axes.at(3).objets_bas, R.axes.at(3).objets_haut, 3, "Côté négatif", "Côté positif", n: 5)

*Axe 5 (#pc(R.variance.at(4))) : le Tessin contre les Grisons.* Côté négatif, le Sottoceneri (Lugano, Chiasso, le Malcantone). Côté positif, les Grisons romanches, le Haut-Valais, Uri, et, plus curieusement, la ville de Berne. Les objets négatifs touchent aux médias publics (No Billag, SSR à 200 francs), à la fiscalité des entreprises et au financement de la route ; le Tessin y a voté plus à droite que son profil. Côté positif, la loi sur la chasse, les soins infirmiers et l'asile. L'axe suit la force de la Lega (r = #num(R.force_partis.Lega.axes.at(4))). C'est un axe tessinois plus qu'un clivage national.

#poles(R.axes.at(4).objets_bas, R.axes.at(4).objets_haut, 4, "Côté négatif", "Côté positif", n: 5)

*Axe 6 (#pc(R.variance.at(5))) : fragile.* Il oppose les communes industrielles du Mittelland soleurois et d'Ajoie (Obergerlafingen, Gunzgen, Boncourt) aux communes paysannes de montagne (Oberland bernois, Prättigau, Appenzell). Côté positif, la réforme LPP, RIE III et le régime financier. Côté négatif, l'antiterrorisme, Frontex, le Gothard et la 13#super[e] rente. On peut y lire une opposition entre salariés et indépendants, mais l'axe est absent des votes de 2014 à 2019 : mieux vaut ne pas le nommer.

#poles(R.axes.at(5).objets_bas, R.axes.at(5).objets_haut, 5, "Côté négatif", "Côté positif", n: 5)

*À retenir.* Les axes 4 et 5 ont presque la même variance (#pc(R.variance.at(3), d: 2) et #pc(R.variance.at(4), d: 2)). Une variante de calcul suffit à les échanger ou à les mélanger (§ 6). Il faut les lire ensemble, comme un plan régional latin : catholicisme alpin d'un côté, spécificité tessinoise de l'autre.

// ════════════════════════════════════════════════════════════════════════════
= La rotation : deux dimensions classiques
// ════════════════════════════════════════════════════════════════════════════

L'ACP choisit ses axes pour maximiser la variance, pas pour qu'ils aient un sens. Quand deux dimensions pèsent à peu près autant, elle les combine volontiers en diagonales. La rotation varimax corrige cela : elle fait tourner les premiers axes jusqu'à ce que chaque objet se rattache le plus possible à un seul facteur.

Appliquée aux axes 1 et 2, elle les fait tourner de #num(R.angle_rotation, d: 1)°. Appliquée aux axes 1 à 3, elle laisse l'axe 3 presque intact (ressemblance de #num(R.facteurs.at(2).congruence_axes.at(2)) sur 1). Les trois facteurs gardent ensemble les #pc(R.variance.at(0) + R.variance.at(1) + R.variance.at(2), d: 0) des trois premiers axes, répartis autrement :

- *F1 · gauche – droite* (#pc(R.facteurs.at(0).variance, d: 0) de la variance) ;
- *F2 · ouverture – souverainisme* (#pc(R.facteurs.at(1).variance, d: 0)) ;
- *F3 · écologie – bloc bourgeois*, l'ancien axe 3 (#pc(R.facteurs.at(2).variance, d: 0)).

#figure(image("figures/plan_facteurs.pdf", width: 94%),
  caption: [Le plan tourné (facteurs F1 et F2, en écarts-types). Les acteurs forment toujours un triangle, désormais posé sur les deux dimensions. Le coin « gauche souverainiste » n'a pas de grand parti.])

*F1, gauche – droite.* Ce sont les objets où la gauche était seule contre tous (§ 2) :

- l'État social : AVS 21, 13#super[e] rente, primes, EFAS, surveillance des assurés ;
- la redistribution : logements, bourses, AVSplus ;
- l'armée : avions de combat, service civil ;
- quelques réformes de société soutenues par la gauche et le centre.

Le facteur se confond avec le Röstigraben : la langue explique à elle seule #pc(R.r2_communes_rot.at("Langue").at(0), d: 0) de la position des communes. En moyenne cantonale, le Jura est le plus à gauche, puis Neuchâtel, Genève, Vaud et Fribourg ; Nidwald, Obwald, Zoug, Appenzell Rhodes-Intérieures et Lucerne ferment la marche. À l'intérieur d'une même région, le niveau de vie semble départager les communes. Le pôle droit, ce sont les communes aisées de la Goldküste zurichoise et de Schwyz (Uitikon, Zumikon, Herrliberg, Wollerau). Le pôle gauche, ce sont les communes ouvrières de l'Ouest lausannois, de l'Arc jurassien et de Genève (Renens, La Chaux-de-Fonds, Avully).

*F2, ouverture – souverainisme.* Ce sont les objets où l'UDC était seule contre tous :

- l'immigration : « 10 millions », limitation, renvoi, Ecopop ;
- l'Europe : directive sur les armes, Frontex ;
- les lois COVID et l'e-ID ;
- le climat quand il est porté par les autorités : loi CO2, loi sur le climat ;
- l'argent liquide, la SSR, la burqa.

Le facteur ne doit presque rien à la langue (R² #num(R.r2_communes_rot.at("Langue").at(1))). Il suit l'opposition ville–campagne : l'urbanisation et la taille en expliquent #pc(R.r2_communes_rot.at("Langue + urbanisation + taille").at(1), d: 0), la force des partis #pc(R.r2_communes_rot.at("Force des partis (2023)").at(1), d: 0). L'indice de suivi du PVL s'y confond presque (r = #num(R.suivi.PVL.facteurs.at(1))) : le PVL est le parti le plus exactement placé sur ce facteur. Côté ouverture, on trouve Bâle-Ville, Genève, Vaud, Zoug et Zurich, avec La Côte vaudoise, Ennetbaden et la ville de Berne. Côté souverainisme, la Suisse centrale (Muotathal, Unteriberg, Rothenthurm), l'Emmental et, plus surprenant, le Jura.

#figure(image("figures/cercle_facteurs.pdf", width: 96%),
  caption: [Les objets dans le plan tourné (corrélation de chaque objet avec F1 et F2). Couleur : le facteur auquel l'objet se rattache le plus, sur trois facteurs.])

#grid(columns: (1fr, 1fr), column-gutter: 8pt,
  figure(image("figures/carte_F1.png", width: 100%), caption: [F1, gauche – droite.]),
  figure(image("figures/carte_F2.png", width: 100%), caption: [F2, ouverture – souverainisme.]),
)

*Quatre quadrants.* Dans le plan tourné, on lit :
- *la droite ouverte* : le PLR, le Centre, le PVL, le Conseil fédéral, economiesuisse, et les communes aisées (Zoug, Goldküste, La Côte) ;
- *la droite souverainiste* : l'UDC, l'UDF, la Suisse centrale et l'Oberland ;
- *la gauche ouverte* : le PS, les Verts, les grandes villes et l'Arc lémanique urbain ;
- *la gauche souverainiste* : sans grand parti, elle rassemble le PST-POP, le MCG et la Lega, et une partie du Jura et du Tessin.

L'axe 1 du site est la diagonale qui va de la droite souverainiste à la gauche ouverte. C'est pour cela qu'il pèse autant : la plupart des communes et des partis s'y alignent. L'axe 2 est l'autre diagonale.

#figure(
  table(
    columns: (1.4fr, auto, ..range(6).map(_ => 1fr)),
    ..entete("Ville", "Canton", "Axe 1", "Axe 2", "Axe 3", "F1", "F2", "F3"),
    filet,
    ..R.villes.map(v => (v.nom, v.canton, ..v.axes.slice(0, 3).map(x => cce(x, 1.5)), ..v.facteurs.map(x => cce(x, 2.5)))).flatten(),
  ),
  caption: [Quelques villes : leur position sur les trois premiers axes et sur les trois facteurs tournés. La teinte donne le sens et l'intensité.],
)

*Correspondance avec Hermann et Leuthold.* Dans leur _Atlas der politischen Landschaften_ (2003), Michael Hermann et Heiri Leuthold avaient tiré trois dimensions des votes de 1982 à 2002 dans 3 021 communes :
- links–rechts : redistribution et sécurité ;
- liberal–konservativ : politique extérieure et de société ;
- ökologisch–technokratisch : environnement et transports.

Nos trois facteurs, tirés de votes vingt ans plus récents par une autre méthode, les retrouvent presque terme à terme. F1 rassemble la redistribution et l'armée, F2 l'Europe, l'immigration et les mœurs, F3 l'environnement, les routes et la fiscalité des entreprises. Deux déplacements méritent d'être notés. Les réformes de société (mariage pour tous, congé paternité) se partagent désormais entre F1 et F2. Et F2 a absorbé, depuis 2020, la confiance envers les autorités (lois COVID, e-ID, argent liquide).

// ════════════════════════════════════════════════════════════════════════════
= Plusieurs manières de nommer les axes
// ════════════════════════════════════════════════════════════════════════════

Chaque grille de lecture a ses preuves et ses angles morts. Le tableau les confronte, axe par axe ; la recommandation suit.

#figure(
  table(
    columns: (auto, 1fr, 1fr, 1fr, 1fr, 1fr),
    align: left + top,
    ..entete("", "Partisane", "Clivages classiques", "Hermann et Leuthold", "Thématique", "Sociogéographique"),
    filet,
    [*Axe 1*], [gauche ↔ UDC (R² PS : #num(R.r2_objets.at("Mot d'ordre PS").at(0)))], [les deux clivages, socio-économique et culturel, alignés], [links–rechts et liberal–konservativ mélangés], [identité, souveraineté, société contre armée et contrôle], [Romandie et villes ↔ Suisse centrale rurale],
    filet,
    [*Axe 2*], [camp gouvernemental ↔ sans parti (R² PLR : #num(R.r2_objets.at("Mot d'ordre PLR").at(1)))], [confiance ↔ défiance envers les autorités ; centre ↔ périphérie], [liberal–konservativ moins links–rechts], [retraites et lois d'application ↔ initiatives populaires], [Goldküste, Zoug ↔ Jura, périphérie latine],
    filet,
    [*Axe 3*], [gauche, Verts ↔ bloc bourgeois avec l'UDC], [post-matérialisme ↔ matérialisme], [ökologisch–technokratisch], [agriculture écologique, imposition des riches ↔ fiscalité des entreprises, routes], [villes alémaniques ↔ montagne, tourisme, Romandie],
    filet,
    [*Axe 4*], [Centre (ex-PDC)], [clivage confessionnel (Rokkan)], [—], [famille, santé ↔ bioéthique, mœurs], [Haut-Valais, Tessin ↔ Vaud protestant],
    filet,
    [*Axe 5*], [Lega], [centre ↔ périphérie (Tessin)], [—], [médias publics, routes ↔ chasse, asile], [Grisons, montagne ↔ Sottoceneri],
    filet,
    [*Axe 6*], [—], [salariés ↔ indépendants ?], [—], [LPP, fiscalité ↔ sécurité, 13#super[e] rente], [Oberland ↔ Mittelland industriel],
    filet,
    [*F1*], [gauche seule contre (R² PS : #num(R.r2_objets_rot.at("Mot d'ordre PS").at(0)))], [socio-économique : État ↔ marché], [links–rechts], [État social, santé, redistribution, armée], [Röstigraben (R² langue : #num(R.r2_communes_rot.at("Langue").at(0)))],
    filet,
    [*F2*], [UDC seule contre (suivi PVL : r = #num(R.suivi.PVL.facteurs.at(1)))], [culturel : intégration ↔ démarcation (Kriesi)], [liberal–konservativ], [immigration, Europe, COVID, numérique, climat], [ville ↔ campagne],
  ),
  caption: [Cinq grilles de lecture pour chaque axe du site et pour les deux premiers facteurs tournés.],
)

*Grille partisane.* C'est la mieux étayée pour les trois premiers axes : les six grands partis expliquent entre #pc(R.r2_objets.at("Six grands partis").at(2), d: 0) et #pc(R.r2_objets.at("Six grands partis").at(0), d: 0) de la position des objets. Elle a deux défauts. Elle date : un libellé comme « PBD » n'aurait plus de sens aujourd'hui. Et elle ne sait pas nommer le côté positif de l'axe 2, que ne porte aucun grand parti.

*Grille des clivages classiques.* Le socio-économique et le culturel au sens de Kriesi et al. (2008), le confessionnel au sens de Rokkan, le centre–périphérie. Elle est la plus générale et la plus durable. Mais elle ne s'applique proprement qu'aux facteurs tournés : l'axe 1 du site mélange les deux premiers clivages.

*Grille de Hermann et Leuthold.* Elle a l'avantage d'une référence suisse connue, fondée sur la même matière (des votes communaux) et vérifiée ici vingt ans plus tard. Elle aussi vaut pour les facteurs tournés plus que pour les axes bruts.

*Grilles thématique et sociogéographique.* Ce sont les plus parlantes pour un lecteur du site, puisqu'elles décrivent ce que montrent la carte et le cercle des corrélations. Mais elles décrivent l'axe sans l'expliquer, et elles dépendent des objets votés : un seul scrutin très régional peut les déplacer.

== Notre lecture

+ *Pour les six axes tels que l'ACP les calcule,* un libellé court, partisan ou géographique, qui se vérifie d'un coup d'œil sur la carte :
  - axe 1 : « gauche – UDC » ;
  - axe 2 : « contestation – camp gouvernemental » ;
  - axe 3 : « écologie urbaine – bloc bourgeois » ;
  - axe 4 : « catholique – protestant » ;
  - axe 5 : « Grisons – Tessin ».

  L'axe 6 est trop fragile pour être nommé. Les § 3.1 à 3.4 donnent pour chaque axe une phrase d'explication.
+ *Pour comprendre la politique suisse,* le plan tourné est plus parlant que celui des axes 1 et 2 : F1 gauche–droite, F2 ouverture–souverainisme, et F3 écologie–bloc bourgeois. Il sépare ce que l'axe 1 mélange : la question sociale et la question identitaire.

// ════════════════════════════════════════════════════════════════════════════
= Ces axes sont-ils solides ?
// ════════════════════════════════════════════════════════════════════════════

Un nom n'a de valeur que si l'axe qu'il désigne résiste aux choix de calcul et à l'ajout de nouveaux votes. Nous avons refait l'ACP de cinq autres manières et comparé chaque fois les axes obtenus à ceux du site.

#let diag(m) = range(6).map(i => calc.abs(m.at(i).at(i)))
#let meilleur(m) = range(6).map(i => calc.max(..m.at(i).map(calc.abs)))
#figure(
  table(
    columns: (2.6fr, ..range(6).map(_ => 1fr)),
    ..entete("Variante", "Axe 1", "Axe 2", "Axe 3", "Axe 4", "Axe 5", "Axe 6"),
    filet,
    [Chaque commune pesant selon son nombre d'électeurs], ..diag(R.robustesse.ponderee.congruence).map(r2c),
    [Chaque objet ramené à la même échelle], ..diag(R.robustesse.reduite.correlation).map(r2c),
    [Votes de 2014 à 2019 seulement (#R.robustesse.periodes.at("2014-2019").objets objets)], ..diag(R.robustesse.periodes.at("2014-2019").correlation).map(r2c),
    [Votes de 2020 à 2026 seulement (#R.robustesse.periodes.at("2020-2026").objets objets)], ..diag(R.robustesse.periodes.at("2020-2026").correlation).map(r2c),
    ..if R.robustesse.ajout != none {
      ([Sans le dernier scrutin (#R.robustesse.ajout.objets_avant objets)], ..diag(R.robustesse.ajout.correlation).map(r2c))
    } else { () },
  ),
  caption: [Ressemblance entre chaque axe et l'axe de même rang obtenu autrement, de 0 (sans rapport) à 1 (identique).],
)

- *L'axe 1 ne bouge pas*, quelle que soit la variante (0,94 à 1).
- *Les axes 2 et 3 forment un plan stable, mais leur partage dépend du calcul.* Avec la pondération par la taille, ou sur les seuls votes de 2014 à 2019, ils se mélangent en partie. Sur 2020-2026, ils sont presque identiques à ceux du site : c'est l'arrivée des votes « de confiance » qui a fixé l'axe 2.
- *Les axes 4 et 5 s'échangent ou se mélangent* dès qu'on change la pondération ou la réduction. Leur plan est stable ; leur ordre ne l'est pas.
- *L'axe 6 n'existe pas avant 2020.*
- *L'ajout du 14 juin 2026 ne change rien*, et les signes sont conservés.

En résumé : les trois premiers axes sont solides, et c'est sur eux que repose l'essentiel de ce document. Les axes 4 et 5 se lisent mieux ensemble, et l'axe 6 est à prendre avec précaution.

// ════════════════════════════════════════════════════════════════════════════
= Classification des objets
// ════════════════════════════════════════════════════════════════════════════

Chaque objet est rangé dans la famille du facteur tourné auquel il se rattache le plus : c'est la plus forte de ses trois corrélations au carré avec F1, F2 et F3. La classification ne dépend donc pas du thème de l'objet mais de la manière dont il a été voté. Le tableau la croise avec le thème. L'annexe B donne la famille de chaque objet.

#let familles = range(3).map(f => R.objets.filter(o => o.dimension == f))
#let themes = R.objets.map(o => o.theme).dedup().sorted()
#figure(
  table(
    columns: (2.2fr, 1fr, 1fr, 1fr, 0.8fr),
    ..entete("Thème", "F1 gauche–droite", "F2 ouverture–souv.", "F3 écologie–bloc", "Total"),
    filet,
    ..themes.map(t => {
      let n = range(3).map(f => familles.at(f).filter(o => o.theme == t).len())
      (t, ..n.map(x => table.cell(align: right, fill: if x > 0 { BLEU.transparentize(100% - calc.min(x / 12, 1) * 45%) } else { none })[#if x > 0 [#x]]), table.cell(align: right)[#n.sum()])
    }).flatten(),
    filet,
    [*Total*], ..range(3).map(f => table.cell(align: right)[*#familles.at(f).len()*]), table.cell(align: right)[*#R.objets.len()*],
  ),
  caption: [Les #R.objets.len() objets par thème et par famille (facteur dominant de la rotation à trois facteurs).],
)

*Ce que montre le croisement.*

- *L'État social et la santé sont presque entièrement sur F1.* Retraites, primes, EFAS, surveillance des assurés.
- *L'immigration et l'Europe sont sur F2.* C'est aussi le cas de la santé quand elle touche aux libertés (lois COVID, liberté vaccinale).
- *L'environnement se partage entre les trois familles.* Il est sur F1 quand la gauche le porte seule (économie verte, fonds climat), sur F2 quand les autorités le portent contre l'UDC (loi CO2, loi sur le climat), et sur F3 quand il touche à l'agriculture et au territoire (pesticides, eau potable, mitage).
- *La fiscalité se partage entre F1 et F3.* Elle est sur F1 pour les impôts des ménages, sur F3 pour ceux des entreprises et des grandes fortunes.

Le thème ne suffit donc pas à prévoir comment un objet sera voté : il faut savoir qui le porte et contre qui.

#for f in range(3) [
  == Famille #DIM_COURT.at(f) : #DIMENSION.at(f) (#familles.at(f).len() objets)
  #let liste = familles.at(f).sorted(key: o => -o.facteurs.at(f))
  #set text(7.8pt)
  #let par_colonne = calc.ceil(liste.len() / 3)
  #grid(columns: (1fr, 1fr, 1fr), column-gutter: 8pt,
    ..range(3).map(c => {
      let morceau = liste.slice(calc.min(c * par_colonne, liste.len()), calc.min((c + 1) * par_colonne, liste.len()))
      stack(spacing: 3.2pt, ..morceau.map(o => [#text(fill: if o.facteurs.at(f) >= 0 { BLEU } else { ROUGE })[#sg(o.facteurs.at(f))] #o.etiquette #text(fill: MUET)[#annee(o)]]))
    }))
]

Dans chaque liste, le signe dit de quel côté du facteur sont les partisans de l'objet. En F1, un signe positif veut dire que les oui venaient de la gauche ; en F2, de l'ouverture ; en F3, de l'écologie et de la gauche alternative.

*Objets mal représentés.* Pour la moitié des objets, les six axes captent plus de #pc(R.objets.map(o => o.qualite).sorted().at(calc.quo(R.objets.len(), 2)), d: 0) de la variance communale. Quelques-uns y passent mal, avec moins de la moitié : ce sont surtout des initiatives sans parti ou des objets très régionaux.
#{
  let faibles = R.objets.filter(o => o.qualite < 0.5).sorted(key: o => o.qualite)
  faibles.map(o => o.etiquette + " (" + annee(o) + ", " + num(o.qualite) + ")").join(", ")
}. Ils ne devraient pas servir à nommer un axe.

#pagebreak()
#heading(level: 1, numbering: none)[Annexe A · Fiches des objets qui définissent les axes]
// ════════════════════════════════════════════════════════════════════════════

Pour chacun des #fiches.len() objets qui définissent le mieux les facteurs et les axes, la fiche donne (l'enjeu de chaque objet est en annexe B) :
- un commentaire et les mots d'ordre ;
- les dissidences cantonales ;
- le résultat par région et par type de commune ;
- la position sur les six axes du site et les trois facteurs.

« lib. » regroupe la liberté de vote, le vote blanc et l'absence de mot d'ordre.

#let fiche(id, texte) = {
  let o = O.at(id)
  let g = o.groupes
  let ce = o.cantons_extremes
  let acteurs = ("CF", "UDC", "PLR", "Centre", "PVL", "PS", "Verts", "USS", "USP", "economiesuisse")
  let libelles = ("CF", "UDC", "PLR", "Centre", "PVL", "PS", "Verts", "USS", "USP", "éco.")
  block(breakable: false, width: 100%, above: 1.1em, below: 0.4em)[
    #text(10pt, weight: "bold")[#o.titre]
    #h(0.4em) #text(8pt, fill: ENCRE2)[#date_fr(o) · #o.type · #if o.type_court == "QS" [#pc(o.oui) pour l'initiative] else [#pc(o.oui) de oui, #if o.accepte [accepté] else [rejeté]#if o.cantons_oui != none and o.type_court in ("RO", "IP", "CP") [ ; cantons : #num(o.cantons_oui, d: 1).replace(",0", "") oui, #num(o.cantons_non, d: 1).replace(",0", "") non]]]
    #v(-0.3em)
    #text(8.8pt)[#texte]
    #v(-0.2em)
    #set table(align: center + horizon)
    #table(
      columns: (auto, ..range(10).map(_ => 1fr)),
      inset: (x: 2.5pt, y: 2pt),
      text(fill: MUET)[Mots d'ordre], ..libelles.map(l => text(fill: MUET, l)),
      [], ..acteurs.map(a => parole(o.paroles.at(a))),
    )
    #v(-0.5em)
    #table(
      columns: (auto, ..range(7).map(_ => 1fr)),
      inset: (x: 2.5pt, y: 2pt),
      text(fill: MUET)[Part de oui], ..("Romandie", "Suisse além.", "Tessin", "Villes", "Campagnes", "Canton min.", "Canton max.").map(l => text(fill: MUET, l)),
      [], ..("romandie", "alemanique", "italophone", "urbain", "rural").map(x => pc(g.at(x), d: 0)),
      [#ce.first().at(0) #pc(ce.first().at(1) / 100, d: 0)], [#ce.last().at(0) #pc(ce.last().at(1) / 100, d: 0)],
    )
    #v(-0.5em)
    #table(
      columns: (auto, ..range(6).map(_ => 1fr), 0.3fr, ..range(3).map(_ => 1fr)),
      inset: (x: 2.5pt, y: 2pt),
      text(fill: MUET)[Corrélation], ..("axe 1", "axe 2", "axe 3", "axe 4", "axe 5", "axe 6").map(l => text(fill: MUET, l)), [], ..("F1", "F2", "F3").map(l => text(fill: MUET, l)),
      [], ..o.axes.map(v => cc(v)), [], ..o.facteurs.map(v => cc(v)),
    )
    #if o.dissidences.len() > 0 {
      v(-0.4em)
      text(7.5pt, fill: ENCRE2)[Sections cantonales dissidentes : #o.dissidences.pairs().map(((p, l)) => p + " (" + l.join(", ") + ")").join(" ; ").]
    }
  ]
}

#for (id, texte) in fiches { fiche(id, texte) }

// ════════════════════════════════════════════════════════════════════════════
#pagebreak()
#heading(level: 1, numbering: none)[Annexe B · Les #R.objets.len() objets]
// ════════════════════════════════════════════════════════════════════════════

Par ordre chronologique. Type : RO référendum obligatoire, RF référendum facultatif, IP initiative populaire, CP contre-projet direct, QS question subsidiaire, où « oui » veut dire préférer l'initiative. Mots d'ordre dans l'ordre Conseil fédéral, UDC, PLR, Centre, PVL, PS, Verts. Famille : le facteur tourné dominant (§ 7).

#{
  set text(7.2pt)
  set par(justify: false)
  let rang(v) = if v == none { text(fill: MUET, "·") } else if v == 1 { text(fill: BLEU, weight: "bold", "+") } else if v == -1 { text(fill: ROUGE, weight: "bold", "−") } else { text(fill: ENCRE2, "0") }
  table(
    columns: (auto, 1fr, auto, auto, auto, auto, auto, auto, auto),
    align: (x, y) => (if x in (0, 1, 2, 4) { left } else { right }) + top,
    inset: (x: 3pt, y: 2.4pt),
    table.header(
      ..entete("Date", "Objet et enjeu", "Type", "Oui", "Mots d'ordre", "Axe 1", "Axe 2", "Axe 3", "Famille"),
      filet,
    ),
    ..R.objets.sorted(key: o => o.date + str(o.sujet_id)).map(o => (
      date_fr(o),
      [*#o.titre*. #o.enjeu #text(fill: MUET)[#o.theme.]],
      o.type_court,
      table.cell(align: right)[#pc(o.oui, d: 1)#if o.type_court != "QS" [#linebreak()#text(fill: if o.accepte { BLEU } else { ROUGE })[#if o.accepte [acc.] else [rej.]]]],
      box[#("CF", "UDC", "PLR", "Centre", "PVL", "PS", "Verts").map(a => rang(o.paroles.at(a))).join(h(1.5pt))],
      cc(o.axes.at(0)), cc(o.axes.at(1)), cc(o.axes.at(2)),
      [#DIM_COURT.at(o.dimension) #text(fill: MUET)[#sg(o.facteurs.at(o.dimension), d: 2)]],
    )).map(ligne => (..ligne, table.hline(stroke: 0.3pt + GRILLE))).flatten(),
  )
}

// ════════════════════════════════════════════════════════════════════════════
#pagebreak()
#heading(level: 1, numbering: none)[Annexe C · Sources et limites]

*Mots d'ordre.* Un mot d'ordre « oui » compte +1, « non » −1. La liberté de vote, le vote blanc et l'absence de mot d'ordre comptent 0. Un parti qui n'existait pas encore, ou dont le mot d'ordre est inconnu, est laissé de côté. Pour une question subsidiaire, « oui » veut dire préférer l'initiative au contre-projet. Avant la fusion de 2021, le Centre prend le mot d'ordre du PDC.

*Communes.* Seules sont retenues les communes qui ont voté sur tous les objets, dans leurs limites actuelles : une commune fusionnée porte les voix de ses anciennes communes. Les circonscriptions des Suisses de l'étranger font partie de l'ACP, mais pas des moyennes par langue ni des cartes. Les résultats cantonaux cités sont recalculés à partir des résultats communaux.

*Rotation.* Méthode varimax, appliquée aux trois premiers axes. Chaque facteur est orienté pour que le PS soit du côté positif de F1, le PLR du côté positif de F2 et les Verts du côté positif de F3.

*Limites.*
- Chaque commune compte pour une, quelle que soit sa taille : les petites communes rurales pèsent autant que les villes. Une ACP où chaque commune pèse selon son nombre d'électeurs garde pourtant le même axe 1 et des axes 2 et 3 voisins (§ 6).
- Placer un parti comme une commune fictive suppose que tout son électorat suit ses mots d'ordre, ce qui n'est jamais le cas. Ces positions décrivent les partis, pas leurs électeurs.
- Les enjeux sont résumés en une ou deux phrases et ne rendent pas compte des campagnes.
- Les axes décrivent des communes, pas des personnes : dire qu'une commune est « à gauche » ne dit rien de chacun de ses habitants.

*Sources.*
- Swissvotes, la base de données des votations fédérales, Année politique suisse, Université de Berne (consultée le 18 septembre 2026).
- Office fédéral de la statistique : résultats des votations populaires par commune ; élections au Conseil national, force des partis par commune ; répertoire officiel des communes.
- Hermann, M. et Leuthold, H. (2003), _Atlas der politischen Landschaften. Ein weltanschauliches Porträt der Schweiz_, vdf.
- Kriesi, H. et al. (2008), _West European Politics in the Age of Globalization_, Cambridge University Press.
