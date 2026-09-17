# Plan d'amélioration du modèle d'extrapolation

Issu de la campagne de backtest des 16-17 septembre 2026. Le travail complet
— protocole, chiffres, impasses — vit sur la branche
`moteur/backtest-ordre-depouillement` (`RESULTATS_BACKTEST.md`, ~450 lignes,
et `analyses/`). Ce fichier n'en garde que les décisions.

**Rien de ce qui suit ne doit être appliqué avant le scrutin du 27 septembre
2026.** Chaque étape change les valeurs projetées et demande une revalidation.

---

## Ce qu'on sait maintenant

Le modèle actuel (6 composantes d'ACP, régression pondérée par les bulletins)
sort une erreur médiane de **0,45 point** à 25 % de dépouillement, contre
3,2 points pour un dépouillement nu. Il n'a **aucun biais systématique** : sous
un ordre d'arrivée aléatoire, le biais signé est de +0,02 point.

Le problème n'est donc pas le cas moyen, c'est la queue : quelques votations
restent à 2-3 points d'erreur pendant une bonne partie de la soirée. Les six
concernées servent de banc d'essai (`analyses/facteurs.py`).

Trois causes distinctes, et c'est pourquoi aucun levier unique ne suffit :

| objet | R² | σ résiduel | remède |
|---|---|---|---|
| 2018-11-25 vaches à cornes | 0,33 | 7,08 | modèle trop pauvre → plus d'axes |
| 2020-02-09 logements abordables | 0,93 | 3,60 | résidu aligné sur la taille → colonne taille |
| 2025-09-28 impôt immobilier | 0,83 | 5,90 | dispersion pure → rien à ce jour |

---

## A. Nombre de composantes de l'ACP  *(gain principal)*

**A1.** Faire varier le nombre de composantes retenues par `populate_pca`
(aujourd'hui 6 en dur). Passer à ~20 fait tomber l'erreur médiane de 0,445 à
0,337 point, et les six pires de 1,385 à 0,749.

**A2.** Rendre ce nombre **croissant avec le dépouillement** plutôt que fixe.
À 20 composantes le modèle a 21 paramètres : les backtests ne descendent pas
sous 5 % d'avance, où le levier deviendrait dangereux. Une règle du type
`p = min(20, nb_communes // 10)` sécurise le début de soirée. **À mesurer
avant de choisir la règle.**

**A3.** Relever le garde-fou de `get_extrapolation`, aujourd'hui à 7 communes
pour 7 paramètres. Il doit suivre le nombre de paramètres effectif.

## B. Pondération de l'ACP  *(gratuit, sans risque)*

**B1.** Pondérer l'ACP par la taille des communes : centrage sur la moyenne
pondérée puis SVD de `√w·(X − μ_w)`, projection ensuite de toutes les communes.
Aujourd'hui `PCA().fit_transform(X)` met Zurich et un hameau de 50 électeurs
sur le même pied, alors qu'on cherche à prédire le vote *des électeurs*.

Gain seul : 0,445 → 0,366 point. Quelques lignes dans `populate_pca`, **aucun
changement dans `extrapolation.py`**. C'est le meilleur rapport gain/risque du
plan et il peut partir seul.

## C. Taille de la commune comme régresseur  *(conditionnel)*

**C1.** Ajouter `log₁₀(electeur_election_precedente)`, centré-réduit, comme
colonne du design. Sur les six pires : 1,385 → 0,784 — une seule colonne vaut
treize axes d'ACP. Elle règle les logements abordables (2,27 → 0,76).

**Seconde réserve, vue sur la figure `distribution_objets`** : la variante riche
écrase la queue mais **dégrade une dizaine d'objets faciles** — 2021-06-13 passe
de 0,77 à 1,32 point, 2020-09-27 de 0,12 à 0,69. Un modèle plus riche aide là où
c'est difficile et ajoute du bruit là où c'était déjà simple. La médiane globale
s'améliore quand même (0,43 → 0,34), mais la dispersion entre objets augmente :
c'est un arbitrage à assumer, pas un gain net.

**Réserve bloquante** : elle dégrade les faibles avances (0,599 → 0,748 à 10 %),
parce que l'ordre de dépouillement trie par taille — à faible avance le
coefficient est estimé sur une plage étroite puis extrapolé avec un levier
élevé. Elle n'est acceptable que si le premier affichage se fait bien vers 25 %.

**C2.** **Vérifier l'hypothèse « premier dépouillement ≈ 25 % »**, qui est
posée et non mesurée. Les `kommunale_resultate_*.json` (ZH, AG, GR) portent des
horodatages communaux et permettraient de la trancher. C'est un préalable à C1.

## C bis. Régularisation progressive  *(optionnel, à explorer)*

**C3.** Plutôt que d'activer ou non la colonne taille selon un seuil d'avance,
la faire monter **en continu** : une pénalité ridge sur son seul coefficient,
dont la force décroît à mesure que l'échantillon dépouillé devient
représentatif en taille.

Le constat qui motive l'idée : à 5 % d'avance, ni les axes supplémentaires ni
l'effet canton ne dégradent — 20 axes + canton, soit 47 colonnes, est même la
meilleure variante à cette avance. **Seule la taille dégrade**, dans les quatre
configurations testées. Ce n'est donc pas un problème de nombre de paramètres
face au nombre d'observations, mais d'**échantillonnage de cette variable-là** :
l'ordre de dépouillement trie par taille, donc à faible avance on n'observe que
des petites communes et le coefficient est extrapolé hors domaine.

Deux conséquences. Le bon critère n'est pas un seuil sur l'avance — arbitraire
et fragile — mais l'étendue de `log(taille)` observée chez les communes
dépouillées rapportée à celle du pays, ou le levier de cette colonne : deux
quantités calculables à chaque mise à jour, qui s'adapteraient d'elles-mêmes à
un dimanche où un gros canton dépouille tôt. Et une transition continue évite
le **saut de courbe** qu'un interrupteur produirait en pleine soirée : basculer
de modèle déplacerait le %oui projeté d'un demi-point sans qu'aucun bulletin
nouveau ne le justifie, ce qui est mauvais sur un affichage en direct.

Si ça marche, C2 (vérifier l'hypothèse des 25 %) devient moins critique : le
modèle s'apercevrait tout seul qu'il n'a pas de quoi estimer le coefficient.

## D. Fourchette d'incertitude

**D1.** Remplacer le ±2,5 points en dur par une fourchette **calibrée
empiriquement** sur les trajectoires d'erreur du backtest, en fonction de
l'avance.

**D2.** Ne pas chercher d'indicateur de fiabilité en direct : sur 22 métriques
testées (σ résiduel, outliers, leviers, jackknife par canton, sensibilités),
**aucune** ne prédit l'erreur d'une soirée donnée (|ρ| ≤ 0,12 d'un ordre
d'arrivée à l'autre). Plusieurs repèrent les objets difficiles (ρ 0,4-0,58),
de quoi moduler la fourchette **par objet**, d'un facteur ~1,5 au plus.

## E. Cartes  *(voie I)*

**E1.** Le krigeage des résidus par voisinage prédit le résidu d'une commune non
dépouillée avec r = 0,42, sans consommer de degré de liberté. Inutile pour la
projection nationale, mais il améliorerait nettement les valeurs communales
affichées sur les cartes choroplèthes. À proposer à la voie I.

**E2.** Les cartes ne distinguent toujours pas visuellement réel et estimé
(`run_extrapolation` écrit les valeurs extrapolées dans `ResultatCommunalEnCours`).
Indépendant de E1, et plus important.

---

## Impasses — ne pas y revenir sans élément nouveau

| piste | résultat |
|---|---|
| Krigeage pour la projection nationale | r = 0,42 par commune, **nul** sur l'agrégat : les résidus in-sample sont de somme pondérée nulle, la correction transportée l'est aussi |
| Clustering appris des régions | battu par le canton (gain 4,6 % contre 7,6 %), ARI 0,03 : les découpages officiels encodent déjà la structure |
| Effet canton dans le design | réel à 6 axes (1,385 → 0,990), redondant à 20 (0,749 → 0,718) |
| Autres typologies OFS (urbanisation, montagne, type de commune) | < 3 % de la variance résiduelle ; l'ACP les capture déjà |
| Poids de régression « optimal » `1/(σ² + p(1−p)/n)` | la pire variante après le non-pondéré : on minimise l'erreur d'un agrégat, pas la variance de β |
| Enrichir le corpus de l'ACP | une ACP qui *contient l'objet du jour* ne fait que 1,101 sur les six pires — moins bien que la colonne taille. La limite est la troncature, pas le corpus |
