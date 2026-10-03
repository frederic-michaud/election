# Ce que le backtest a appris du modèle

Campagne de septembre 2026 : rejouer des votations passées sous différents
ordres d'arrivée des communes. Détail, chiffres et scripts :
`RESULTATS_BACKTEST.md` au tag `backtest-2026-09` ;
synthèse : [`synthese_backtest.pdf`](synthese_backtest.pdf).

- **Le modèle actuel** (6 axes d'ACP, régression pondérée) : erreur médiane
  de 0,45 point à 25 % de dépouillement, contre 3,2 points pour le
  dépouillement brut, et aucun biais systématique.
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
