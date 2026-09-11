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
10 % d'avance : elle atténue le biais d'ordre, elle ne l'annule pas.

## Le point central : quand les adversariaux se rejoignent

| écart entre les deux adversariaux | avance médiane | min | max |
|---|---|---|---|
| < 5 pt | 46,5 % | 20,3 % | 80,4 % |
| < 2 pt | 73,2 % | 50,3 % | 93,9 % |
| **< 1 pt** | **84,2 %** | **60,7 %** | **100 %** |
| < 0,5 pt | 92,5 % | 70,9 % | 100 % |

**La borne pessimiste de la méthode est ~84 % d'avance.** En-deçà, il existe un
ordre d'arrivée qui laisse plus d'un point d'incertitude. Ce qui rend le site
utile à 10 % d'avance repose donc entièrement sur l'hypothèse que l'ordre réel
n'est pas adversarial — hypothèse que la régression sur les
`kommunale_resultate_*` soutient (la taille domine, le %oui n'est pas
significatif, t = −1,5).

## Le levier remplace-t-il le « ≥ 7 communes » ?

Pouvoir discriminant (AUC sur « erreur < 1 point »), pool équilibré = les trois
ordres à poids égal :

| prédicteur | pool équilibré | réaliste seul | adversariaux |
|---|---|---|---|
| **levier max** | **0,787** | 0,711 | 0,918 |
| communes dépouillées | 0,757 | 0,711 | 0,894 |
| avance | 0,638 | 0,712 | 0,955 |

L'avance est le meilleur prédicteur *dans* un scénario et le pire *entre*
scénarios : elle ne sait pas qui manque. Le levier est le seul prédicteur
agnostique à l'ordre d'arrivée.

Sur son vrai métier — bloquer l'absurde : les 55 instantanés au-delà de 100
points d'erreur ont tous **7 à 9 communes** et un levier ≥ 1,7.

- seuil **levier ≤ 1,7** : les élimine tous, garde **99,1 %** du pool ;
- seuil **≥ 10 communes** : les élimine tous, garde **97,8 %**.

À pire-cas égal, part du pool admise : 1,42× plus de points admis par le levier
à 10 points de pire cas, 1,30× à 2 points, mais 0,86× à 20 points — l'avantage
est réel mais modeste et pas uniforme.

**Recommandation.** Remplacer `if len(...) < 7` par un test sur `max hᵢ` des
communes manquantes :

1. **levier > 1,7** → ne rien afficher (remplaçant direct du « ≥ 7 communes »,
   il est strictement plus sûr : le seuil actuel laisse passer 55 projections
   au-delà de 100 points d'erreur, dont certaines au-dessus de 100 % de oui) ;
2. **levier > ~1,5·10⁻⁴** → afficher en signalant que c'est indicatif.

Ce n'est pas un certificat de fiabilité : même au seuil le plus sévère, la
précision sur « erreur < 1 point » plafonne vers 90 %. Le levier est un bon
filtre d'absurdité ; le certificat, lui, n'existe pas avant ~84 % d'avance, et
c'est un fait sur la méthode, pas sur son implémentation.

## Limites

- Les communes arrivent **une par une**, jamais par blocs cantonaux. Les vrais
  scrutins arrivent par blocs, ce qui devrait dégrader le réaliste. Étape
  suivante.
- `electeur_election_precedente` vient de l'objet précédent de la base : les
  communes fusionnées entre-temps ne sont pas rejouées à la frontière de
  l'époque.
- La loi d'arrivée est calibrée sur 5 cantons (ZH/AG/GR/SZ/ZG), R² = 0,29,
  σ = 46 min. Les cantons romands, plus rapides, ne sont pas représentés.

## Fichiers

Commités : le script, `backtest_synthese.csv`, ce document. Non commités
(`var/` ignoré) : `courbes.csv.gz` (588 k instantanés), `objet_*.png`,
`recapitulatif.png`, `snapshot.sqlite3`.
