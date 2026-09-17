# Backtest de l'extrapolation face à l'ordre de dépouillement

Branche `moteur/backtest-ordre-depouillement`, **jamais destinée à `master`**.

```bash
cp /home/ubuntu/politiques-prod/var/votation.sqlite3 var/backtest/snapshot.sqlite3
python manage.py backtest_ordre_depouillement --test-equivalence
python manage.py backtest_ordre_depouillement --tirages 100 --graine 0 --grille 200
python manage.py backtest_ordre_depouillement --analyse-garde-fou
```

Lecture seule : la base est ouverte par `sqlite3` en `mode=ro&immutable=1`, jamais
par l'ORM. Ni `PCAResult` ni `ResultatCommunalEnCours` ne sont touchés ; l'ACP de
chaque date cible est recalculée en mémoire sur les seuls objets antérieurs.

## Données

103 objets réels, 36 dates, 2014-11-30 → 2026-06-14 ; 2 122 communes dont 7 à
l'historique incomplet — **2 115 retenues, 0,01 % des électeurs perdus**.

**30 cibles** : seuil de 20 objets antérieurs ⟹ éligibilité à partir du
2016-11-27. L'historique importé a des trous (2023 n'a qu'une date, 2019 et 2025
en ont trois), donc la règle « 4 objets par année » sélectionne de fait toutes
les dates éligibles, une par date.

## Correction : l'axe des abscisses

**Première version fausse.** L'axe x était `avance = dépouillé / total *projeté*`,
la grandeur affichée par le site. Elle dépend du modèle : quand le modèle délire
à faible effectif, l'avance affichée délire aussi et devient non monotone. En
triant par avance avant d'interpoler, des points pris à 10 communes dépouillées
se retrouvaient reportés au milieu de la courbe, avec des erreurs jusqu'à 82 000
points, qui contaminaient les moyennes sur tirages.

L'axe est maintenant `avance = bulletins dépouillés / bulletins totaux`,
monotone par construction, et la commande **lève une erreur** si l'axe cesse
de l'être. L'avance affichée est conservée comme colonne : elle s'écarte de la
vraie de **0,6 point médian** (p95 1,1) dans le scénario réaliste — elle est donc
fiable, ce n'était pas là le problème.

Effet de la correction : l'erreur max médiane du réaliste passe de 4,16 à
**1,12 point**. Les chiffres ci-dessous sont ceux d'après correction.

## Étape 1 — lstsq vs `scipy.optimize.minimize`

`Delta_fast` est un moindres carrés pondérés : `β = lstsq(√w·X, √w·y)`.
Équivalence vérifiée — **écart max 1,6·10⁻⁸ à 3,1·10⁻⁸** sur les 7 paramètres,
`Delta` identique à 10 chiffres, sur 4 masques tirés (199 à 1 354 communes).

**Sauf près du garde-fou, et ça concerne la production :**

| communes | écart max (20 tirages) | Δ(lstsq) | Δ(minimize) |
|---|---|---|---|
| 7 | **7,2·10⁻⁴** | 1,2·10⁻²⁷ | 3,4·10⁻⁹ |
| 10 | 3,7·10⁻⁶ | 9,67616 | 9,67616 |
| 100 | 9,2·10⁻⁸ | 106,193 | 106,193 |

À 7 points pour 7 paramètres le système est exactement déterminé : `lstsq`
interpole, le BFGS s'arrête sur tolérance. Passer `get_linear_parameter` en
solution fermée est une correction, pas seulement une optimisation.

Le balayage vectorisé (rang 1 par `cumsum`) reproduit la fonction pure au bit
près sur les 6 effectifs testés.

## Étape 3 — coût

0,038 s par tirage supplémentaire. Run complet (30 cibles × 100 tirages,
grille 200) : **136 s, pic 224 Mo, aucun swap**.

## Résultat principal : l'extrapolation contre le dépouillement nu

« Dépouillement nu » = `oui_connu / exprimés_connus`, ce qu'afficherait le site
sans extrapoler. Médianes sur les 30 objets, en points de %oui :

### Ordre réaliste

| avance | extrapolation | dépouillement nu | gain | objets où l'extrapolation est pire |
|---|---|---|---|---|
| 10 % | **0,54** | 3,74 | **6,9×** | 5/30 |
| 25 % | **0,42** | 3,55 | **8,5×** | 3/30 |
| 50 % | **0,29** | 3,18 | **11,0×** | 2/30 |
| erreur max sur la trajectoire | **1,12** | 4,12 | 3,7× | — |
| avance pour rester sous 1 pt | **0,4 %** | 91,1 % | — | — |

**C'est ça, l'apport de l'extrapolation** : le dépouillement nu met 91 %
d'avance à descendre sous un point, l'extrapolation y est dès le début de la
soirée. Le biais « petites communes d'abord » vaut 3 à 4 points et ne se résorbe
qu'à la toute fin ; l'extrapolation le corrige presque entièrement.

La nuance : **sur 5 objets sur 30, l'extrapolation est moins bonne que le
dépouillement nu à 10 % d'avance**. Ce sont les objets où le biais d'ordre est
naturellement faible (2022-02-13 : le nu est à 0,5 point, l'extrapolation en
ajoute 2,5). Le modèle corrige un biais qui n'existait pas.

### Ordres adversariaux

| avance | extrap. bas | nu bas | extrap. haut | nu haut |
|---|---|---|---|---|
| 10 % | 8,45 | 16,45 | 8,49 | 17,94 |
| 25 % | 5,21 | 12,59 | 4,33 | 14,13 |
| 50 % | 2,67 | 8,27 | 2,16 | 8,27 |
| avance sous 1 pt | 75,5 % | 96,9 % | 75,5 % | 96,9 % |

L'extrapolation divise l'erreur par 2 à 4 même contre un ordre adversarial, et
n'est jamais pire (0/30 et 1/30 objets). Mais elle reste à 8 points d'erreur à
10 % d'avance : elle atténue le biais d'ordre, elle ne l'annule pas. Voir plus
bas : ces deux ordres ne sont pas atteignables en pratique.

## Les ordres adversariaux sont-ils des pires cas atteignables ? Non.

Frédéric a objecté qu'un biais aussi systématique sur la courbe *extrapolée*
n'avait pas de raison d'être. Vérification faite, **le code est juste, mais
l'objection touchait juste** : le protocole était trop pessimiste.

Recoupement supplémentaire : sur un ordre adversarial, le balayage vectorisé
et les fonctions de production elles-mêmes (`get_linear_parameter`, donc
`scipy.optimize.minimize`) donnent le même %oui projeté à **3·10⁻⁶ – 3·10⁻⁵
point** près, à k = 50, 200, 800 et 1 500.

**Le code d'abord.** Sur des données engendrées exactement par le modèle
(résidu nul), le biais adversarial vaut **2·10⁻¹² point** — fit, agrégation,
ordre et balayage sont donc corrects. Et sur un objet réel, une projection
« oracle » (mêmes données, mêmes ordres, mais paramètres ajustés sur *toutes*
les communes) est exacte à **0,2–0,3 point** à toutes les avances, pendant que
la projection ajustée sur le sous-ensemble se trompe de 10,9 points. Tout le
biais vient donc des paramètres ajustés, pas de la mécanique.

**D'où vient le biais.** Trier par %oui ne sélectionne pas seulement des
*profils* non représentatifs — ça, le modèle le corrige parfaitement. Ça
sélectionne sur le **résidu**, la part du %oui que les 6 composantes
n'expliquent pas (R² pondéré médian 0,81, σ résiduel **3,3 points**). La
régression ne peut pas distinguer « ces communes ont un résidu négatif » de
« le niveau général est plus bas » : elle absorbe l'écart dans la constante et
l'applique à tout le monde. Reconstruction à partir de rien, sur données
synthétiques avec le seul résidu ajouté :

| σ résidu | tri par %oui | tri par composante ACP 1 |
|---|---|---|
| 0 pt | 0,00 | 0,00 |
| 2,0 pt | 5,92 | 0,58 |
| **3,3 pt (le réel)** | **7,91** | **0,25** |
| 5,0 pt | 11,78 | 0,18 |

Le σ réel reproduit à lui seul les 8,45 points observés. À résidu identique, un
tri sur le *profil* ne coûte que 0,25 point.

**Conséquence.** Le résidu est par construction imprévisible depuis
l'historique : un ordre d'arrivée qui lui serait corrélé exigerait de connaître
le résultat à l'avance. Les deux courbes `adversarial_*` sont donc des **bornes
d'oracle**, pas des ordres qu'un processus réel puisse produire. Ma conclusion
précédente — « la borne pessimiste est 84 % d'avance » — était trop sévère.

Le vrai pire cas atteignable est un ordre corrélé à quelque chose d'observable
d'avance : le profil politique, la langue, le canton. D'où les deux scénarios
`profil_bas` / `profil_haut`, qui trient sur la 1ʳᵉ composante ACP.

### Biais systématique contre dispersion

Distinction essentielle, et que la première version du rapport confondait : la
médiane de |erreur| mélange un décalage systématique et de la dispersion autour
de zéro. Colonne de gauche |erreur|, colonne du milieu l'écart **signé**,
médianes sur 30 objets à 10 % d'avance :

| scénario | \|erreur\| | **biais signé** | objets sous la vérité |
|---|---|---|---|
| adversarial bas (oracle) | 8,45 | **−8,45** | 100 % |
| adversarial haut (oracle) | 8,49 | **+8,49** | 7 % |
| profil bas | 1,68 | **+0,31** | 47 % |
| profil haut | 4,61 | **−0,68** | 57 % |
| réaliste | 0,54 | **+0,11** | 43 % |
| *dépouillement nu — réaliste* | 3,74 | **−2,17** | 80 % |
| *dépouillement nu — profil bas* | 11,82 | **−8,21** | 80 % |
| *dépouillement nu — profil haut* | 12,41 | **+7,97** | 20 % |

**Le dépouillement nu a un biais systématique dans tous les scénarios, et
l'extrapolation le supprime quasi entièrement** : −2,17 → +0,11 en réaliste,
−8,21 → +0,31 en profil bas, +7,97 → −0,68 en profil haut. Pour tout ordre
d'arrivée atteignable, le biais résiduel de la projection est **sous 0,7 point
et de direction aléatoire** (47 % / 57 % / 43 % d'objets sous la vérité, soit
du 50-50). Ce qui reste dans la colonne |erreur| est de la dispersion, pas un
décalage.

Les deux seuls scénarios à biais systématique sont ceux qui trient sur le
résultat lui-même — 100 % et 93 % des objets du même côté.

### Pourquoi le tri sur le %oui biaise, et pas le tri sur le profil

Simulation directe, `y = 0,10·x + 0,45 + ε`, σ(ε) = 3,3 pt, 4 000 tirages :

| sélection | k | biais moyen | écart-type | P(biais < 0) |
|---|---|---|---|---|
| sur **x** | 5 | +0,13 | 33,8 | 51,3 % |
| sur **x** | 20 | −0,01 | 7,4 | 49,6 % |
| sur **x** | 200 | −0,00 | 1,0 | 50,6 % |
| sur **y** | 5 | −20,2 | 11,4 | 96,8 % |
| sur **y** | 20 | −15,2 | 4,2 | **100 %** |
| sur **y** | 200 | −7,3 | 0,8 | **100 %** |

Sélectionner sur la variable explicative donne un estimateur non biaisé, juste
très dispersé à petit k — l'erreur de **pente** est symétrique. Sélectionner
sur la variable expliquée biaise le **niveau** : la droite ajustée passe par le
centroïde des points retenus, qui ont tous un résidu du même signe, et la
constante étant partagée, la prédiction est décalée partout.

### Les quatre bornes, médianes sur 30 objets

| scénario | err@10 % | err@25 % | err@50 % | nu @10 % |
|---|---|---|---|---|
| adversarial bas (oracle) | 8,45 | 5,21 | 2,67 | 16,45 |
| adversarial haut (oracle) | 8,49 | 4,33 | 2,16 | 17,94 |
| **profil bas (atteignable)** | **1,68** | **1,34** | **0,72** | 11,82 |
| **profil haut (atteignable)** | **4,61** | **1,99** | **0,89** | 12,41 |
| réaliste | 0,54 | 0,42 | 0,29 | 3,74 |

Avance à laquelle les deux bornes se rejoignent (écart < 1 point) :

| paire de bornes | médiane | min | max |
|---|---|---|---|
| oracle (tri sur le %oui) | 84,2 % | 60,7 % | 100 % |
| **prévisible (tri sur le profil)** | **50,3 %** | **24,5 %** | **77,9 %** |

**La borne pessimiste réellement atteignable est donc ~50 % d'avance, pas
84 %.** Et sous un ordre hostile mais prévisible, l'extrapolation tient déjà
sous 2 points dès 10 % d'avance — contre 12 points pour le dépouillement nu —
sans biais systématique (voir ci-dessus) : ce qui reste est de la dispersion.

**Une réserve sérieuse malgré tout** : `profil_haut` explose à très faible
avance — erreur médiane **21,6 points** en dessous de 2 % d'avance, jusqu'à
3 064 points. Compter d'abord un bloc politiquement homogène force la
régression à extrapoler vers l'autre extrémité du spectre, avec un levier
énorme. C'est un mode de défaillance physiquement atteignable (un canton qui
dépouille vite et vote d'un bloc), et c'est exactement ce que le levier détecte.


## Le r de Pearson prédit-il l'erreur ? Non

Ajouté le 2026-09-16, à la demande de Frédéric : si le r observable en direct
suivait l'erreur, on tiendrait un indicateur de fiabilité gratuit le jour J.

Run dédié, **scénario réaliste seul**, 30 objets × 100 tirages d'ordre
d'arrivée, grille 200 (`--scenarios realiste`, sortie `var/backtest/realiste_r/`).
Les médianes du run principal sont reproduites à l'identique (err@10 % 0,54,
nu 3,74, err max 1,12) — pas de régression.

Deux corrélations de Pearson entre %oui prédit et %oui réel, à chaque avance,
non pondérées :

- **dedans** (in-sample) : sur les communes déjà dépouillées, celles qui servent
  à l'ajustement. C'est le seul des deux qu'on puisse calculer le jour J.
- **dehors** : sur les communes restantes — la vraie qualité prédictive, connue
  seulement après coup.

Les deux figurent au panneau du bas de chaque `objet_*.{png,pdf}` : trait = un
tirage, bande = 95 % des 100 tirages.

**Forme des courbes.** Le r dedans démarre déjà à ~0,80 dès les premières
communes et ne bouge quasiment plus de la soirée ; le r dehors monte lentement
de 0,80 à 0,90. Aucun des deux ne signale quoi que ce soit au moment où la
projection est la plus fragile.

**Croisement r / erreur, sur les 30 objets** (médianes sur les tirages) :

| avance | r dedans médian | \|err\| médiane | corr(r, \|err\|) | Spearman |
|---|---|---|---|---|
| 5 % | 0,819 | 0,64 | −0,14 | −0,29 |
| 10 % | 0,832 | 0,57 | −0,16 | −0,29 |
| 25 % | 0,847 | 0,42 | −0,19 | −0,24 |
| 50 % | 0,856 | 0,30 | −0,16 | −0,26 |

Le signe est le bon — r plus haut, erreur plus faible — mais l'ampleur est
négligeable sur 30 points. Et **au sein d'un même objet, d'un ordre d'arrivée à
l'autre, la corrélation est nulle** : médiane +0,00, quartiles −0,07 / +0,18.
Le r ne dit donc pas si *cette* soirée-là se passe bien.

**Pourquoi**, et c'est cohérent avec le mécanisme de la section précédente :
l'erreur vient du **résidu moyen des communes dépouillées**, que la régression
absorbe dans la constante. Le r mesure la **dispersion** du résidu, pas sa
moyenne sur l'échantillon retenu — il reste à 0,85 pendant que la constante
part de travers. Un indicateur de fiabilité doit porter sur le résidu moyen
pondéré, pas sur r. Le levier reste, à ce stade, le seul détecteur utile.

Réserve : les deux r sont non pondérés alors que l'ajustement est pondéré par
les bulletins.

## Témoin : ordre complètement aléatoire — pas de biais ville/campagne résiduel

Ajouté le 2026-09-16. L'ordre « réaliste » trie de fait par taille de commune
(retard = 80·log10(électeurs) + bruit) : s'il reste un biais ville/campagne que
le modèle ne corrige pas, c'est là qu'il se voit. Le témoin est une
**permutation uniforme** des communes, sans aucune structure de taille
(`--scenarios aleatoire`, 30 objets × 100 tirages, grille 200).

Médianes sur les 30 objets, en points de %oui :

| | extrap. @10 % | extrap. @50 % | biais signé @10 % | nu @10 % | biais nu @10 % |
|---|---|---|---|---|---|
| ordre réaliste | 0,54 | 0,29 | +0,11 | 3,74 | **−2,17** |
| **ordre aléatoire** | **0,12** | **0,02** | **+0,02** | **0,19** | **−0,11** |

**Deux conclusions.**

D'abord, le biais de −2,17 points du dépouillement nu en ordre réaliste est
**entièrement un effet d'ordre** : sous permutation uniforme, le dépouillement
nu lui-même tombe à −0,11 point de biais et 0,19 point d'erreur dès 10 %
d'avance. Ce n'est pas une propriété des communes, c'est le fait que les
petites arrivent en premier.

Ensuite, et c'est la réponse à la question posée : **l'extrapolation
n'introduit aucun biais propre**. Sur un échantillon représentatif par
construction, elle sort +0,02 point de biais signé, avec 43 % des objets sous
la vérité — du 50-50. Il n'y a donc pas de biais ville/campagne résiduel caché
dans l'ACP ou dans la pondération par les bulletins.

Réserve, la même que partout : l'erreur **max** sur la trajectoire atteint 146
points en moyenne sur tirages, pour une médiane de 1,63. C'est la queue à très
faible avance — sept communes tirées au hasard peuvent donner une matrice mal
conditionnée. Le levier reste le bon détecteur.

## Quelles métriques annoncent une projection qui rate ?

Ajouté le 2026-09-16. Puisque le r de Pearson échoue, on teste une batterie
d'indicateurs calculables le jour J sur les seules communes déjà dépouillées
(`var/metriques_fiabilite.py`, 30 objets × 60 tirages d'ordre réaliste, aux
avances 5 %, 10 % et 25 %).

Point de départ : pour chaque commune on calcule sa **volatilité historique**,
l'écart-type de son résidu au modèle sur tous les objets passés. Une commune
« normalement bien prédite » est une commune dont ce résidu est petit
d'habitude — on peut donc voir si elle décroche le jour J.

Deux familles : les **dispersions** (σ pondéré, R², σ du jour sur σ historique,
médiane de |résidu|/volatilité, poids des communes à plus de 2σ ou 3σ de leur
propre norme, versions restreintes aux communes fiables et de taille moyenne,
kurtosis) et les **sensibilités** (jackknife par canton, correction par résidu
cantonal, poids des cantons pas encore entamés, saut de la projection entre la
moitié de l'échantillon et maintenant, part de variance des résidus expliquée
par le canton ou par le degré d'urbanisation).

### Entre objets : oui, ça marche

Corrélation de rang avec l'erreur médiane, sur les 30 objets :

| métrique | @5 % | @10 % | @25 % |
|---|---|---|---|
| saut de projection | 0,48 | **0,52** | **0,58** |
| jackknife par canton | 0,42 | 0,46 | 0,41 |
| σ résiduel pondéré | 0,49 | 0,43 | 0,45 |
| excès sur communes fiables | 0,49 | 0,40 | 0,38 |
| poids d'outliers > 2σ | 0,45 | 0,43 | 0,40 |
| part de variance urbanisation | 0,31 | 0,32 | 0,34 |
| *r de Pearson (rappel)* | *−0,29* | *−0,29* | *−0,24* |

Stables aux trois avances, p entre 0,002 et 0,03. C'est nettement mieux que le r.

### Mais elles disent presque toutes la même chose

σ, excès sur communes fiables, poids d'outliers et σ/σ_historique sont corrélés
entre eux **de 0,85 à 0,99** : c'est un seul indicateur sous quatre noms. En
corrélation partielle, à σ contrôlé, il ne reste que :

| métrique | brut | à σ contrôlé |
|---|---|---|
| saut de projection | +0,52 | **+0,35** |
| jackknife par canton | +0,46 | +0,22 |
| part de variance urbanisation | +0,32 | **+0,20** |
| poids d'outliers > 2σ | +0,43 | +0,11 |
| excès sur communes fiables | +0,40 | +0,09 |

L'idée des « communes normalement prédictibles qui décrochent » **fonctionne**
(0,40 brut) mais n'apporte rien au-delà de σ : ces communes décrochent quand
tout décroche. En revanche la part de variance expliquée par le **degré
d'urbanisation** est peu corrélée à σ (0,36) et garde +0,20 — l'effet
ville/campagne résiduel du jour est bien une information distincte.

### Intra-objet : rien, et c'est un résultat

D'un ordre d'arrivée à l'autre au sein d'un même objet, **toutes** les
métriques sont à |ρ| ≤ 0,12, donc nulles. Aucune ne dit si *cette* soirée-là
rate. C'est cohérent avec le mécanisme : l'erreur vient du résidu moyen des
communes dépouillées, quantité orthogonale par construction à tout ce qu'on
observe in-sample.

### Ampleur pratique, et réserve

Les six objets les plus ratés contre les six mieux réussis :

| | \|err\| médiane | saut | σ | jackknife | excès fiables |
|---|---|---|---|---|---|
| mieux réussis | 0,19 | 0,29 | 3,59 | 0,11 | 0,64 |
| plus ratés | 2,06 | 0,51 | 4,16 | 0,16 | 0,77 |

L'erreur varie d'un facteur 10, les métriques d'un facteur 1,2 à 1,8
seulement. Elles permettent donc de **moduler** une fourchette par objet d'un
facteur ~1,5 à 2, pas de la prédire finement.

Réserves : 22 métriques × 3 avances font 66 tests, donc quelques p < 0,05 sont
attendus par hasard — seules les métriques stables aux trois avances sont
retenues ci-dessus. Et 30 objets, c'est peu pour ajuster quoi que ce soit de
fin.

**Conséquence pour la fourchette** : une fourchette calibrée empiriquement par
objet, modulée par le saut de projection et σ, avec l'urbanisation comme
second axe. Pas de fourchette conditionnelle à la soirée — rien d'observable ne
la porte.

## Les 27 colonnes OFS qu'on n'importe pas : c'est la géographie qui compte

Ajouté le 2026-09-16. `data/agvch_niveaux_2026-01-01.csv` porte **29 colonnes**
et `import_metadata_commune` n'en lit que deux (`SPRGEB2020` → langue,
`DEGURB2021` → degré d'urbanisation). Les 27 autres sont des nomenclatures
officielles : typologie des communes, ville/campagne, montagne, agglomération,
bassin d'emploi, régions statistiques.

Test (`var/meta_communes.py`) : on ajuste le modèle de production sur *toutes*
les communes, et on regarde quelle part de la variance pondérée des résidus
chaque variable explique — donc ce qu'elle apporterait **en plus** des 6
composantes de l'ACP. Contrôle par permutation obligatoire : une variable à 144
classes explique mécaniquement beaucoup, même au hasard.

Médianes sur les 30 objets :

| variable | classes | réelle | au hasard | **gain** |
|---|---|---|---|---|
| `DistrictId` | 144 | 46,7 % | 14,2 % | **32,4 %** |
| `BAE2018` (bassins d'emploi) | 101 | 43,2 % | 10,9 % | **32,3 %** |
| `CantonId` | 26 | 32,3 % | 4,1 % | **28,2 %** |
| `STREG2022` (régions stat.) | 13 | 25,8 % | 2,1 % | **23,6 %** |
| `GBAE2018` (bassins regroupés) | 16 | 25,6 % | 2,3 % | **23,2 %** |
| `AGGL2020` (agglomération) | 85 | 26,6 % | 5,6 % | 21,0 % |
| `REGCH` (grandes régions) | 7 | 11,6 % | 1,0 % | 10,6 % |
| `AGGLGK2020` (taille agglo) | 6 | 3,7 % | 0,8 % | 2,9 % |
| `GDETYP2020_25` (type de commune) | 25 | 5,9 % | 3,5 % | 2,4 % |
| `SPRGEB2020` (langue) | 4 | 1,9 % | 0,4 % | 1,5 % |
| `GDETYP2020_9` | 9 | 2,6 % | 1,4 % | 1,2 % |
| `DEGURB2021` (urbanisation) | 3 | 0,8 % | 0,4 % | 0,4 % |
| `MONT2019` (montagne) | 2 | 0,5 % | 0,1 % | 0,3 % |
| `STALAN2020` (ville/campagne) | 3 | 0,7 % | 0,5 % | 0,3 % |

**La coupure est franche.** Tout ce qui est *géographique* — district, bassin
d'emploi, canton, région — explique 20 à 32 % de la variance résiduelle. Tout
ce qui est *typologique* — degré d'urbanisation, montagne, ville/campagne, type
de commune — explique moins de 3 %, et la langue 1,5 %.

**Interprétation.** L'ACP, construite sur 55+ votations, a déjà absorbé les
dimensions urbain/rural et linguistique : les ajouter au modèle ne servirait à
rien. C'est cohérent avec le témoin en ordre aléatoire, qui ne montre aucun
biais ville/campagne résiduel. Ce qui reste hors de portée des 6 composantes,
c'est un **effet régional par objet** — un canton qui, sur *cette* votation-là,
vote 3 points à côté de son profil habituel. Et c'est exactement le mode de
défaillance que le jackknife par canton détectait.

**Piste à tester.** Ajouter un effet régional au design. Deux réserves
sérieuses : ces parts sont mesurées in-sample, donc le gain en projection reste
à établir par backtest ; et le jour J à faible avance, beaucoup de régions n'ont
encore aucune commune dépouillée — des effets fixes cantonaux (26 paramètres de
plus pour 7 actuels) seraient ingérables. Il faut un rétrécissement vers zéro,
donc un modèle mixte. `STREG2022` (13 classes, 23,6 %) et `GBAE2018` (16
classes, 23,2 %) ont le meilleur rapport gain/paramètres — meilleur que le
canton lui-même.

Ordre de grandeur, si le gain se transposait hors échantillon : σ résiduel
passerait de 3,3 à ~2,8 points.

> **À corriger par la section suivante.** Ces parts sont mesurées sur les
> résidus d'un modèle à **6** composantes. Les deux tiers de « l'effet canton »
> sont en réalité de la variance ACP tronquée : à 20 composantes, le canton ne
> capte plus que 10,1 % au lieu de 26,0 %.

## L'effet régional est-il réel, et peut-on apprendre les régions ?

Ajouté le 2026-09-16, sur une question de Frédéric : plutôt que d'imposer
canton ou district, ne pourrait-on pas repérer les communes qui « votent bizarre
en même temps » et en déduire un découpage appris ? Avec une hypothèse de
travail : presse régionale, notable local actif — un choc qui frappe une région
sur *cet* objet-là, indépendamment du positionnement politique habituel.

Protocole (`var/clusters_residus.py`) : résidus des 101 objets antérieurs au
2026-06-14, **clusters appris sur les 67 premiers objets et évalués sur les 34
suivants**. Sans ce partage temporel, n'importe quel clustering explique
parfaitement les données qui l'ont engendré.

### D'abord : les deux tiers de l'effet n'étaient que de la troncature

Part de variance résiduelle expliquée par le découpage, **hors échantillon**,
selon le nombre de composantes gardées :

| composantes | variance ACP retenue | part canton | part district |
|---|---|---|---|
| **6 (production)** | 80,4 % | **26,0 %** | 42,4 % |
| 12 | 86,1 % | 16,6 % | 29,0 % |
| 20 | 89,6 % | **10,1 %** | 22,6 % |
| 30 | 92,3 % | 6,6 % | 18,7 % |
| 50 | 95,8 % | 4,3 % | 15,1 % |

L'essentiel de « l'effet canton » était la variance que la troncature à 6
composantes laisse de côté. Il en reste quelque chose à 20 composantes (10,1 %
contre 2,5 % pour un découpage permuté), mais deux fois et demie moins.

Et ça recoupe les runs `--composantes`, jamais consignés jusqu'ici : l'erreur
médiane à 10 % d'avance passe de **0,52** (6 composantes) à 0,45 (12) et
**0,33** (20), sans dégrader l'erreur max ni le levier.

### Ensuite : le clustering appris ne bat pas les découpages officiels

À nombre de groupes égal, part expliquée hors échantillon (et la même sur
étiquettes permutées, pour la ligne de base) :

| modèle à 6 composantes | groupes | part | au hasard | ARI canton |
|---|---|---|---|---|
| canton (imposé) | 26 | 26,0 % | 3,7 % | 1,00 |
| KMeans sur résidus | 26 | **27,6 %** | 4,1 % | 0,29 |
| district (imposé) | 156 | 42,4 % | 14,2 % | 0,23 |
| KMeans sur résidus | 144 | 44,6 % | 15,4 % | 0,10 |

| modèle à 20 composantes | groupes | part | au hasard | ARI canton |
|---|---|---|---|---|
| canton (imposé) | 26 | **10,1 %** | 2,5 % | 1,00 |
| KMeans sur résidus | 26 | 7,2 % | 2,6 % | 0,03 |
| district (imposé) | 156 | 22,6 % | 10,5 % | 0,23 |
| KMeans sur résidus | 144 | 16,5 % | 12,5 % | 0,01 |

À 6 composantes le clustering appris fait jeu égal avec le canton (gain net
23,5 % contre 22,3 %) — il ne fait que retrouver ce que la troncature a laissé.
À 20 composantes, **le canton fait nettement mieux que le clustering appris**
(gain 7,6 % contre 4,6 %), et l'ARI tombe à 0,03 : le clustering ne retrouve
même plus les cantons, il s'accroche à du bruit. Les découpages de la
Confédération ne sont donc pas arbitraires — ils encodent bien la structure.

### Les modes de co-variation sont géographiques, et de courte portée

Les 12 premiers facteurs de co-variation portent 53,1 % de la variance des
résidus, et ils sont très administratifs :

| facteur | variance | R² canton | R² district |
|---|---|---|---|
| 1 | 9,6 % | 0,57 | 0,73 |
| 2 | 7,6 % | 0,60 | 0,77 |
| 3 | 6,1 % | 0,40 | 0,61 |

Aucune structure cachée qui échapperait aux découpages : le district explique
les trois quarts des deux premiers modes. Et la portée spatiale est courte —
corrélation des résidus entre communes selon la distance :

| distance | 0-5 km | 5-10 | 10-20 | 20-40 | 40-80 | 80-150 |
|---|---|---|---|---|---|---|
| corrélation | **0,31** | 0,25 | 0,17 | 0,07 | −0,00 | −0,02 |

**C'est du local, pas du cantonal** : la corrélation est divisée par deux tous
les 10 km et s'annule à 40 km — l'échelle d'un district ou d'un bassin de vie.
Compatible avec l'hypothèse presse régionale / notable local, moins avec un
effet politique cantonal.

### Conséquence

La priorité n'est pas le clustering appris, c'est **garder plus de composantes
ACP** : c'est gratuit, déjà mesuré (0,52 → 0,33 point à 10 % d'avance), et ça
absorbe les deux tiers de l'effet régional. Ensuite seulement, un effet
**district** rétréci — pas canton — pour le tiers restant.

## Corriger les communes manquantes par leurs voisines (krigeage) : non

Ajouté le 2026-09-16, sur une idée de Frédéric : plutôt que d'ajouter des
composantes à l'ACP — qui supposent que l'effet régional existait déjà dans le
passé, et qui coûtent des degrés de liberté quand seules 30 communes sont
rentrées — estimer le décalage régional **le jour même**, à partir des résidus
des communes voisines déjà dépouillées.

C'est de la régression-krigeage (`var/krigeage_residus.py`). Covariance tirée du
variogramme mesuré sur l'historique (palier 0,31, portée 25 km), donc **aucun
paramètre consommé** sur le fit du jour. Résidus standardisés par la volatilité
historique propre à chaque commune avant transport, 12 plus proches voisins,
30 objets × 10 tirages à 10 % d'avance.

### Au niveau de la commune, ça marche très bien

Corrélation entre le résidu **prédit** par krigeage et le résidu **réel** d'une
commune pas encore dépouillée : **0,423**. Le voisinage explique donc ~18 % de
la variance du résidu individuel — nettement mieux que le seul voisin le plus
proche (0,31). Agréger douze voisins moyenne le bruit idiosyncratique.

### Sur l'agrégat, aucun gain

| méthode | \|err\| médiane | moyenne | p90 |
|---|---|---|---|
| sans correction | 0,593 | 0,873 | **1,972** |
| krigeage | 0,539 | 0,861 | 2,044 |
| moyenne simple des voisins < 15 km | 0,606 | 0,922 | 2,189 |

En comparaison **appariée**, la seule honnête : le krigeage améliore dans
**47 %** des cas, gain médian **−0,008 point**. C'est du pile ou face. L'écart
des médianes marginales (0,539 contre 0,593) est un artefact ; et le p90 se
dégrade.

### Pourquoi — et c'est structurel

La régression pondérée avec constante impose **Σ wᵢ·εᵢ = 0** sur les communes
dépouillées : la moyenne pondérée des résidus observés est nulle *par
construction*. Le krigeage transporte donc vers les communes manquantes une
quantité de moyenne quasi nulle, et `Σ v̂ⱼ·ε̂ⱼ ≈ 0`. Il redistribue
remarquablement bien les résidus dans l'espace, mais il ne peut pas déplacer le
**niveau** — or c'est le niveau qui fait l'erreur d'agrégat, comme la section
sur le mécanisme l'avait déjà établi.

Autrement dit : bien prédire chaque commande ne sert à rien si l'erreur vient
d'une constante partagée. C'est le même mur que pour le r de Pearson, sous une
autre forme.

### Deux enseignements quand même

La variante **naïve** (moyenne simple des voisins à moins de 15 km) **dégrade**
franchement : 0,606 contre 0,593. Elle applique une correction à pleine
amplitude là où la corrélation réelle plafonne à 0,31, donc elle transporte
surtout du bruit. Le rétrécissement du krigeage n'est pas une complication
gratuite : c'est lui qui sépare corriger de dégrader.

Et surtout : avec r = 0,42 au niveau communal, le krigeage **améliorerait
nettement les cartes** choroplèthes, qui affichent aujourd'hui des valeurs
extrapolées commune par commune sans distinguer réel et estimé. Le gain est là,
pas sur le %oui national.

## Pondérer l'ACP par la taille des communes : oui, ça marche

Ajouté le 2026-09-16, sur une question de Frédéric : le fit ne devrait-il pas se
concentrer sur les grosses communes ?

Précision d'abord : **la régression est déjà pondérée** par les bulletins rentrés
(`extrapolation.py:52`). En revanche **l'ACP ne l'est pas** —
`PCA(n_components=6).fit_transform(X)` met Zurich et un hameau de 50 électeurs
sur le même pied. Les 6 axes sont donc choisis pour résumer le vote *des
communes*, alors qu'on veut prédire le vote *des électeurs*.

Test croisé (`var/ponderation.py`, 30 objets × 15 tirages) : ACP uniforme ou
pondérée par la taille (SVD de `√w·(X − μ_w)`, projection ensuite de toutes les
communes), × exposant du poids de régression `w = bulletins^α`. Erreur médiane
en points de %oui :

| ACP | poids fit | @5 % | @10 % | @25 % | @50 % |
|---|---|---|---|---|---|
| uniforme | α = 0 | 1,057 | 0,967 | 0,782 | 0,537 |
| uniforme | α = 0,5 | 0,868 | 0,763 | 0,552 | 0,392 |
| **uniforme** | **α = 1 (production)** | 0,684 | 0,599 | 0,445 | 0,319 |
| uniforme | α = 1,5 | 0,635 | 0,570 | 0,416 | 0,286 |
| uniforme | 1/variance | 0,983 | 0,882 | 0,675 | 0,502 |
| **pondérée** | **α = 1** | **0,611** | **0,525** | **0,366** | **0,274** |
| pondérée | α = 1,5 | 0,588 | 0,524 | 0,373 | 0,271 |
| pondérée | 1/variance | 0,868 | 0,760 | 0,624 | 0,398 |

**Pondérer l'ACP gagne 12 à 18 %** à pondération de fit inchangée : 0,599 → 0,525
à 10 % d'avance, 0,445 → 0,366 à 25 %. En comparaison appariée, plus
conservatrice, le gain médian est de +0,018 point et l'amélioration touche 53 %
des cas — l'ACP pondérée rogne surtout la queue des grosses erreurs.

### Et la pondération du fit devrait être plus forte, pas plus faible

Hypothèse testée et **réfutée** : on pouvait croire que `α = 1` sur-pondère les
grandes villes, puisque le poids optimal au sens des moindres carrés est
`1/(σ² + p(1−p)/n)`, qui sature dès que le résidu structurel (3,3 points)
domine le bruit d'échantillonnage. Cette variante « 1/variance » est en fait la
**pire** de toutes après α = 0 : 0,760 contre 0,525.

L'explication : on ne cherche pas à estimer β efficacement, on cherche à
minimiser l'erreur sur un **agrégat pondéré par les électeurs**. Aligner la
fonction de perte sur la cible l'emporte sur l'efficacité statistique. D'où
α = 1,5 légèrement meilleur que α = 1 aux faibles avances (gain apparié +0,082,
mieux dans 60 % des cas), même si α = 1 reprend l'avantage à 25 %.

### Ce qu'on en fait

Rien avant le 27 septembre — pas de refactoring à quelques jours du scrutin.
Après : **pondérer l'ACP** est le changement le plus sûr et le moins invasif
(quelques lignes dans `populate_pca`, puis re-run ; aucun changement dans
`extrapolation.py`). L'exposant α = 1,5 est un réglage purement empirique sur
30 objets — tentant, mais à revalider avant d'y toucher.

## Synthèse — ce qu'il faut faire, ce qu'il ne faut pas faire

État au 2026-09-17, après la campagne d'exploration des 16 et 17 septembre.

### Le classement des leviers, sur les six objets les plus ratés (à 25 % d'avance)

| variante | 6 pires | médiane @25 % |
|---|---|---|
| dépouillement nu | 4,153 | 3,18 |
| **ACP uniforme · 6 axes — production** | **1,385** | **0,445** |
| ACP 6 axes *incluant l'objet du jour* (oracle) | 1,101 | — |
| ACP pondérée · 6 axes | 1,203 | 0,366 |
| ACP uniforme · 6 axes · canton | 0,990 | 0,369 |
| ACP uniforme · 6 axes · log(taille) | 0,784 | 0,432 |
| ACP uniforme · 20 axes | 0,749 | 0,337 |
| **ACP pondérée · 20 axes · log(taille)** | **0,623** | 0,346 |

### À faire

1. **Passer à ~20 axes d'ACP** (ou un nombre croissant avec le dépouillement).
   C'est le levier le plus fort : −46 % sur les six pires. La troncature à 6 est
   la vraie limite du modèle actuel — et non la qualité du corpus, comme le
   prouve la borne d'oracle ci-dessus.
2. **Pondérer l'ACP par la taille des communes.** Quelques lignes dans
   `populate_pca`, aucun changement dans `extrapolation.py`. Gain modeste mais
   gratuit et sans risque.
3. **Ajouter `log₁₀(electeur_election_precedente)` au design.** Une seule
   colonne vaut treize axes d'ACP sur la queue (0,784 contre 0,749), et elle
   règle le cas des logements abordables (2,27 → 0,76). **Mais elle dégrade les
   faibles avances** (0,599 → 0,748 à 10 %) : elle n'est acceptable que sous
   l'hypothèse « premier dépouillement à 25 % », qui reste à vérifier.

### À ne pas faire

- **Krigeage des résidus par voisinage** : excellent par commune (r = 0,42),
  strictement nul sur l'agrégat (47 % d'amélioration, gain médian −0,008).
  Les résidus in-sample sont de somme pondérée nulle par construction, donc la
  correction transportée a une moyenne nulle. Utile pour **les cartes**, pas
  pour la projection.
- **Clustering appris des régions** : battu par le canton une fois le modèle
  bien spécifié (gain 4,6 % contre 7,6 %), ARI 0,03.
- **Effet canton** : réel, mais redondant avec les axes supplémentaires
  (1,385 → 0,990 à 6 axes, mais 0,749 → 0,718 à 20 axes).
- **Importer plus de typologies OFS** (urbanisation, montagne, type de
  commune) : moins de 3 % de variance résiduelle expliquée. L'ACP les a déjà.
- **Indicateur de fiabilité en direct** : aucune des 22 métriques testées ne
  prédit l'erreur d'une soirée donnée (|ρ| ≤ 0,12 intra-objet). La fourchette
  doit être calibrée par objet, pas conditionnée à la soirée.

### Les trois pathologies

Les objets ratés ne le sont pas pour la même raison, et c'est ce qui explique
qu'aucun levier unique ne les corrige tous :

| objet | R² | σ | pente taille après ACP | remède |
|---|---|---|---|---|
| 2018-11-25 vaches à cornes | **0,33** | 7,08 | 3,58 | plus d'axes (1,58 → 0,20) |
| 2020-02-09 logements | 0,93 | 3,60 | **1,70** | colonne taille (2,27 → 0,76) |
| 2025-09-28 impôt immobilier | 0,83 | **5,90** | 0,71 | aucun (2,76 → 1,57 au mieux) |

Le premier est mal expliqué par le modèle ; le deuxième est bien expliqué mais
son résidu est aligné sur l'ordre d'arrivée ; le troisième est simplement
dispersé, sans structure exploitable.
