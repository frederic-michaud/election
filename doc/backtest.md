# Ce que le backtest a appris du modèle

Campagne de septembre 2026 : rejouer des votations passées sous différents
ordres d'arrivée des communes, et mesurer l'erreur de la projection en
fonction de l'avance. Synthèse : [`synthese_backtest.pdf`](synthese_backtest.pdf) ;
protocole et scripts sur la branche `moteur/backtest-ordre-depouillement`.
Ce qui reste à essayer est dans [`PLAN.md`](../PLAN.md).

## Le modèle actuel

6 composantes d'ACP, régression pondérée par les bulletins : erreur médiane
de **0,45 point** à 25 % de dépouillement, contre 3,2 points pour le
dépouillement brut. **Aucun biais systématique** : sous un ordre d'arrivée
aléatoire, le biais signé est de +0,02 point.

## Juger sur la queue, pas sur la médiane

Le problème n'est pas le cas moyen : ce sont les quelques votations qui
restent à 2–3 points d'erreur pendant une bonne partie de la soirée.
Optimiser la médiane et optimiser la queue ne classent pas les variantes de
la même façon. Toujours reporter, à côté de la médiane, l'erreur sur les six
pires objets :

| Objet | Erreur médiane à 10 % d'avance (points) |
|---|---|
| 2025-09-28 impôt immobilier | 3,83 |
| 2020-02-09 logements abordables | 3,32 |
| 2018-11-25 vaches à cornes | 2,37 |
| 2022-02-13 expérimentation animale | 1,75 |
| 2021-09-26 impôts sur les salaires | 1,51 |
| 2021-03-07 dissimulation du visage | 1,18 |

Trois causes distinctes, d'où l'absence de levier unique :

| Objet | R² | σ résiduel | Remède |
|---|---|---|---|
| vaches à cornes | 0,33 | 7,08 | modèle trop pauvre → plus d'axes |
| logements abordables | 0,93 | 3,60 | résidu aligné sur la taille → colonne taille |
| impôt immobilier | 0,83 | 5,90 | dispersion pure → rien à ce jour |

L'impôt immobilier résiste à toutes les variantes testées, et l'effet canton
l'aggrave : c'est l'objet-test des idées nouvelles.

Les variantes s'évaluent **à 25 % d'avance** (voir
[`depouillement.md`](depouillement.md)) : ne pas écarter une option sur son
seul comportement à 5 %.

## Pas d'indicateur de fiabilité en direct

Sur 22 métriques testées (σ résiduel, valeurs aberrantes, leviers, jackknife
par canton, sensibilités), **aucune** ne prédit l'erreur d'une soirée donnée
(|ρ| ≤ 0,12 d'un ordre d'arrivée à l'autre). Plusieurs repèrent en revanche
les objets difficiles (ρ 0,4 à 0,58) : de quoi moduler la fourchette par
objet, d'un facteur 1,5 au plus.

## Impasses — ne pas y revenir sans élément nouveau

| Piste | Résultat |
|---|---|
| Krigeage pour la projection nationale | r = 0,42 par commune, **nul** sur l'agrégat : les résidus sont de somme pondérée nulle, la correction transportée aussi |
| Clustering appris des régions | battu par le canton (gain 4,6 % contre 7,6 %), ARI 0,03 : les découpages officiels encodent déjà la structure |
| Effet canton dans le design | réel à 6 axes (1,385 → 0,990), redondant à 20 (0,749 → 0,718) |
| Autres typologies OFS (urbanisation, montagne, type de commune) | < 3 % de la variance résiduelle : l'ACP les capture déjà |
| Poids de régression « optimal » `1/(σ² + p(1−p)/n)` | la pire variante après le non-pondéré : on minimise l'erreur d'un agrégat, pas la variance des coefficients |
| Enrichir le corpus de l'ACP | une ACP qui contient l'objet du jour ne fait que 1,101 sur les six pires, moins bien que la colonne taille : la limite est la troncature, pas le corpus |
| Historique long (depuis 2010) | gagne des colonnes mais brouille le profil actuel (dérive démographique) ; et avant fin 2014, les Suisses de l'étranger de plusieurs cantons ne sont pas publiés à part. D'où `--depuis 2014-11-30` |
