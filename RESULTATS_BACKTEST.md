# Backtest de l'extrapolation face à l'ordre de dépouillement

Branche `moteur/backtest-ordre-depouillement`, **jamais destinée à `master`**.
Reproduction :

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
l'historique incomplet (5 sans aucun résultat, 1 à 52/103, 1 à 74/103) — soit
**2 115 communes retenues, 0,01 % des électeurs perdus**. La limite est
négligeable.

**30 cibles** : seuil de 20 objets antérieurs ⟹ éligibilité à partir du
2016-11-27 (21 objets). Aucune année n'atteint 4 dates éligibles sauf 2018, 2021
et 2024 : l'historique fédéral importé a des trous (2023 n'a qu'une date,
2019 et 2025 en ont trois). La règle « 4 objets par année » sélectionne donc de
fait toutes les dates éligibles, une par date.

## Étape 1 — lstsq vs `scipy.optimize.minimize`

`Delta_fast` est un moindres carrés pondérés, linéaire en ses 7 paramètres :
`β = lstsq(√w·X, √w·y)`. En régime normal l'équivalence est vérifiée —
**écart max 1,6·10⁻⁸ à 3,1·10⁻⁸** sur les 7 paramètres, `Delta` identique à
10 chiffres, sur 4 masques tirés au hasard (199 à 1 354 communes dépouillées).

**Mais pas au voisinage du garde-fou**, et ça concerne le code de production :

| communes dépouillées | écart max (20 tirages) | Δ(lstsq) | Δ(minimize) |
|---|---|---|---|
| 7 | **7,2·10⁻⁴** | 1,2·10⁻²⁷ | 3,4·10⁻⁹ |
| 8 | 6,2·10⁻⁵ | 1,92137 | 1,92137 |
| 10 | 3,7·10⁻⁶ | 9,67616 | 9,67616 |
| 15 | 8,0·10⁻⁷ | 4,09401 | 4,09401 |
| 100 | 9,2·10⁻⁸ | 106,193 | 106,193 |

À 7 communes pour 7 paramètres le système est exactement déterminé : `lstsq`
interpole (Δ = 10⁻²⁷), le BFGS s'arrête sur tolérance. C'est **`minimize` qui ne
converge pas**, précisément dans le régime où les coordonnées ACP extrapolées
sont multipliées par des leviers énormes. Passer `get_linear_parameter` en
solution fermée est donc une correction, pas seulement une optimisation.

Le balayage vectorisé (mises à jour de rang 1 par `cumsum`) reproduit la
fonction pure au bit près : avance, %oui, conditionnement et levier identiques à
8 décimales sur 6 effectifs testés.

## Étape 3 — coût

0,9 s/cible à 1 tirage, 2,0 s à 30 tirages ⟹ **0,038 s par tirage
supplémentaire**. Run complet 30 cibles × 100 tirages × grille 200 :
**136 s**, pic mémoire **224 Mo**, aucun swap. Le rang 1 était nécessaire :
3 060 courbes × 200 ajustements BFGS complets auraient coûté des heures.

## Résultats

Médianes sur les 30 objets, en points de %oui :

| scénario | err. max | err@10 % | err@25 % | err@50 % | avance err<1 pt | avance err<0,5 pt |
|---|---|---|---|---|---|---|
| adversarial bas | 25,89 | 8,46 | 5,22 | 2,36 | 0,755 | 0,829 |
| adversarial haut | 25,12 | 8,33 | 4,25 | 2,05 | 0,755 | 0,883 |
| **réaliste (moyenne)** | **4,16** | **0,54** | **0,42** | **0,28** | **0,019** | **0,154** |
| réaliste (enveloppe 97,5 %) | 4,75 | 1,10 | 0,82 | 0,62 | 0,152 | 0,732 |

Les deux adversariaux sortent du cadre ±10 points sur **plus de la moitié de la
trajectoire** (médiane 114 et 118 points de grille sur 200) ; le réaliste n'en
sort jamais (0/200).

**Sous une loi d'arrivée réaliste, la méthode est très bonne** : moins d'un
demi-point d'erreur dès 10 % d'avance en moyenne, et l'enveloppe haute des 100
tirages reste sous 1,1 point. C'est le résultat principal, et il est rassurant.

**Sous un ordre adversarial, elle ne l'est pas** : 8,4 points d'erreur à 10 %
d'avance, encore 2 points à 50 %. La régression pondérée n'a aucune défense
contre un dépouillement corrélé au vote.

### Le point central : quand les adversariaux se rejoignent

| écart entre les deux adversariaux | avance médiane | min | max |
|---|---|---|---|
| < 5 pt | 46,5 % | 20,3 % | 80,4 % |
| < 2 pt | 73,2 % | 50,3 % | 93,9 % |
| **< 1 pt** | **84,2 %** | **58,8 %** | **96,9 %** |
| < 0,5 pt | 92,5 % | 70,9 % | 100 % |

**La borne pessimiste de la méthode est donc ~84 % d'avance** : en-deçà, il
existe un ordre d'arrivée qui laisse plus d'un point d'incertitude, et sur le
pire objet il faut attendre 97 %. Autrement dit : *rien* dans les données du
jour J ne garantit une projection à 1 point avant que le dépouillement soit
quasi terminé. Tout ce qui rend le site utile à 10 % d'avance repose sur
l'hypothèse que l'ordre réel n'est pas adversarial — hypothèse que les
`kommunale_resultate_*` confirment (la taille domine, le %oui n'est pas
significatif, t = −1,5).

### Le levier remplace-t-il le « ≥ 7 communes » ?

**Oui, et le garde-fou actuel ne sert à rien.** Sur le pool équilibré (les trois
ordres à poids égal), « ≥ 7 communes » admet 100 % des instantanés, dont un à
**1 200 points d'erreur** — le %oui projeté sort régulièrement au-dessus de
100 % juste au-dessus du seuil.

Pouvoir discriminant (AUC sur « erreur < 1 point ») :

| prédicteur | pool équilibré | réaliste seul | les deux adversariaux |
|---|---|---|---|
| **levier max** | **0,798** | 0,709 | 0,918 |
| communes dépouillées | 0,770 | 0,709 | 0,894 |
| avance | 0,644 | 0,710 | 0,955 |

L'avance est le meilleur prédicteur *à l'intérieur* d'un scénario et le pire
*entre* scénarios — c'est exactement ce qu'on lui reproche : elle ne sait pas
qui manque. Le levier est le seul prédicteur agnostique à l'ordre d'arrivée.

À pire-cas égal, part du pool admise :

| pire erreur tolérée | seuil levier | admis | seuil communes | admis | gain |
|---|---|---|---|---|---|
| 50 pt | 0,236 | 91,7 % | 26 | 85,7 % | 1,07× |
| 20 pt | 6,8·10⁻⁴ | 40,6 % | 224 | 46,7 % | 0,87× |
| 10 pt | 1,6·10⁻⁴ | 22,3 % | 1 060 | 15,6 % | 1,43× |
| 5 pt | 5,0·10⁻⁵ | 9,4 % | 1 454 | 8,7 % | 1,08× |
| 2 pt | 2,4·10⁻⁵ | 3,2 % | 1 912 | 2,3 % | 1,41× |

Et sur le rôle précis du garde-fou — bloquer les projections absurdes : les 28
instantanés au-delà de 100 points d'erreur ont tous **11 à 13 communes** et un
levier ≥ 275.

- un seuil **levier ≤ 270** les élimine tous en gardant **99,8 %** du pool ;
- un seuil **≥ 14 communes** les élimine tous en ne gardant que **91,4 %**.

**Recommandation.** Remplacer `if len(...) < 7: return 0.5, 0.5, 0` par un test
sur `max hᵢ` des communes manquantes, avec deux niveaux :

1. **levier > 0,3** → ne rien afficher (c'est le remplaçant direct du « ≥ 7
   communes », et il est huit points de couverture plus généreux) ;
2. **levier > ~1·10⁻⁴** → afficher la projection en la signalant comme
   indicative (au-delà, l'erreur peut dépasser 10 points).

Ce n'est pas un signal net de « maintenant on peut y croire » : même au seuil le
plus sévère la précision sur « erreur < 1 point » plafonne vers 90 %. Le levier
est un bon filtre d'absurdité, pas un certificat de fiabilité — ce dernier
n'existe pas avant ~84 % d'avance, et c'est un fait sur la méthode, pas sur son
implémentation.

## Limites

- Les communes arrivent **une par une**, jamais par blocs cantonaux. Les vrais
  scrutins arrivent par blocs, ce qui devrait dégrader le réaliste et rapprocher
  le cas réel des adversariaux. C'est l'étape suivante.
- L'ACP est recalculée à l'antérieur, mais `electeur_election_precedente` vient
  de l'objet précédent de la base : les communes fusionnées entre-temps ne sont
  pas rejouées à la frontière communale de l'époque.
- La loi d'arrivée est calibrée sur 5 cantons (ZH/AG/GR/SZ/ZG), R² = 0,29,
  σ = 46 min. Les cantons romands, plus rapides, ne sont pas représentés.

## Fichiers

Commités : le script, `var/backtest/synthese.csv` (recopié en
`backtest_synthese.csv`) et ce document. Non commités (`var/` est ignoré) :
`courbes.csv.gz` (9,2 Mo, 589 k instantanés), `objet_*.png`, `recapitulatif.png`,
`snapshot.sqlite3`.
