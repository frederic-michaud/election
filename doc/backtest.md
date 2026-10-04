# Ce que le backtest a appris du modèle

Campagne de septembre 2026 : rejouer des votations passées sous différents
ordres d'arrivée des communes. Détail, chiffres et scripts :
`RESULTATS_BACKTEST.md` au tag `backtest-2026-09` ;
synthèse : [`synthese_backtest.pdf`](synthese_backtest.pdf).

- **Le modèle de septembre** (6 axes d'ACP, régression pondérée) : erreur
  médiane de 0,45 point à 25 % de dépouillement, contre 3,2 points pour le
  dépouillement brut, et aucun biais systématique. Depuis octobre : ACP
  pondérée à 16 axes (ci-dessous).
- **Juger sur la queue, pas sur la médiane.** Le problème, ce sont les
  quelques objets qui restent à 2–3 points d'erreur longtemps ; toujours
  reporter leur erreur à côté de la médiane. Le pire : l'impôt immobilier du
  28.09.2025, qui résiste à toutes les variantes.
- **Évaluer à 25 % d'avance** (voir [`depouillement.md`](depouillement.md)).
- **Ce qui aide** : pondérer l'ACP par la taille des communes, et plus d'axes.
- **Pas d'indicateur de fiabilité en direct** : aucune des 22 métriques
  testées ne prédit l'erreur d'une soirée.
- **Impasses** : krigeage des résidus, régions apprises, effet canton (utile
  à 6 axes, redondant à 20), autres typologies OFS, poids de régression
  « optimaux », historique depuis 2010. La taille de la commune comme
  régresseur règle la queue mais dégrade les faibles avances : écartée.

## Octobre 2026 : ACP pondérée, combien d'axes ?

Base réelle, les 63 objets précédés d'au moins 40 votations, 50 tirages
d'ordre réaliste chacun ; erreur en points de % de oui, médiane / moyenne des
six objets les plus ratés.

| ACP | @5 % | @25 % | @75 % |
|---|---|---|---|
| uniforme, 6 axes | 0,74 / 3,66 | 0,45 / 2,28 | 0,21 / 0,77 |
| pondérée, 6 axes | 0,69 / 3,67 | 0,42 / 2,22 | 0,19 / 0,70 |
| pondérée, 10 axes | 0,67 / 3,23 | 0,40 / 1,90 | 0,16 / 0,61 |
| pondérée, 14 axes | 0,56 / 2,36 | 0,29 / 1,25 | 0,12 / 0,40 |
| pondérée, 20 axes | 0,51 / 2,26 | 0,27 / 1,15 | 0,11 / 0,38 |
| pondérée, 30 axes | 0,51 / 2,16 | 0,26 / 1,06 | 0,11 / 0,36 |

- Pondérer l'ACP aide peu ; les axes, beaucoup, et surtout les axes 13 et 14,
  qui séparent les grandes villes entre elles (Genève contre Bâle et
  Lausanne, Zurich contre Neuchâtel et Lugano). Au-delà de 16, le gain est
  faible : on en garde 16.
- Avec peu de communes, plus d'axes nuit : à 40 communes, 6 axes font 1,7
  point d'erreur médiane, 16 axes 2,0. À 16 axes, la projection bat le
  dépouillement brut dès 30 communes (2,7 contre 4,7) mais reste fragile
  (90ᵉ centile 7,0) ; à 50 communes, 1,7 contre 4,4. D'où le garde-fou à 50
  communes plutôt qu'un nombre d'axes croissant.
- `scipy.optimize.minimize` converge toujours à 17 paramètres : écart nul
  avec la solution exacte des moindres carrés.

## Octobre 2026 : la fourchette

Même campagne (63 objets × 50 tirages, ACP pondérée à 16 axes). La fourchette
affichée est l'écart que 95 % des projections ne dépassent pas, en ordre
réaliste ; `manage.py calibrer_fourchette` refait ce calcul et l'écrit dans la
table `Fourchette`. Un bootstrap sur les communes aurait été bien trop étroit :
l'erreur vient d'un décalage commun aux communes dépouillées, qu'il ne
reproduit pas.

En points de % de oui :

| avance | fourchette (95 %, réaliste) | 95 %, cantons par blocs | brut, médiane (90ᵉ c.) réaliste | brut, cantons |
|---|---|---|---|---|
| 1 % | ±3,4 | — | — | — |
| 5 % | ±2,2 | ±5,6 | 4,2 (8,5) | 3,8 (9,6) |
| 10 % | ±1,7 | ±3,8 | 4,1 (8,0) | 3,1 (7,7) |
| 25 % | ±1,2 | ±2,1 | 3,7 (6,9) | 1,8 (4,7) |
| 50 % | ±0,7 | ±1,2 | 3,1 (5,3) | 1,1 (2,7) |
| 80 % | ±0,4 | ±0,6 | 1,7 (3,1) | 0,5 (1,3) |
| 95 % | ±0,2 | ±0,2 | 0,3 (0,8) | 0,2 (0,6) |

- **Deux ordres d'arrivée, deux difficultés.** Dans l'ordre réaliste (petites
  communes d'abord), le brut sous-estime le oui (−1,3 point en médiane à
  25 %) et la projection corrige ce biais. Quand des cantons entiers arrivent
  d'un bloc, le brut est moins biaisé mais la projection doit extrapoler des
  cantons qu'elle n'a pas vus : sa fourchette double.
- **Choix : l'ordre réaliste.** Si une vraie soirée arrive par blocs
  cantonaux, la fourchette est trop étroite. À vérifier sur les instantanés
  du 27.09.2026.
- Aucun objet n'est systématiquement hors fourchette : 2 à 5 sur 63 sortent
  de la fourchette à 90 % dans plus de la moitié de leurs tirages.

