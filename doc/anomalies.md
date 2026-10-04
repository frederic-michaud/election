# Repérer les erreurs de saisie communales

Le profil ACP d'une commune prédit son vote assez bien pour qu'un écart
anormal signale souvent une erreur de saisie, pas un vote surprenant.

## La méthode

Pour chaque objet du scrutin :

1. ajuster le % de oui de toutes les communes sur leur profil ACP, pondéré
   par les voix ;
2. mesurer l'écart de chaque commune en σ, avec une variance qui ajoute à
   l'aléa binomial (`p(1−p)/n`) une dispersion propre à l'objet, estimée sur
   les communes de plus de 500 voix ;
3. ajouter un terme pour la cohérence des bulletins entre objets : une
   commune vote une seule fois, ses bulletins doivent être presque identiques
   d'un objet à l'autre ;
4. pour les communes les plus anormales, essayer les **corrections simples**
   — oui/non inversés sur un objet, objets intervertis, un chiffre mal saisi
   — et retenir celle qui fait le plus baisser le χ². Comparer aussi aux
   communes semblables — parmi les cent plus proches sur la carte, les douze
   au profil ACP le plus proche —, pour écarter un effet régional réel.

Une correction qui ramène le χ² près de zéro est un signal fort ; un écart
élevé sans correction simple qui l'explique est le plus souvent un vrai vote
singulier.

## Sur le site

`manage.py detecter_anomalies` applique cette méthode à chaque tour du jour J,
dès 200 communes dépouillées (`scrutin/anomalies.py`), et la page
`/anomalies` en montre le résultat. Les communes signalées restent dans
l'ajustement.

Deux mesures par commune :

- le **vote** : son écart au profil ACP, en σ, objet par objet ;
- les **bulletins** : l'écart entre ses nombres de bulletins d'un objet à
  l'autre, comparé à son écart habituel — la médiane sur les scrutins passés
  à plusieurs objets, qu'une erreur passée isolée ne déplace pas (Tafers a
  un 29,4 % dans son passé). L'aléa autour de cette habitude vaut environ
  0,35 % des bulletins, mesuré sur l'historique ; s'y ajoute un aléa de
  comptage, et un écart de moins de 10 bulletins ne compte pas. Une grande
  commune est donc jugée plus sévèrement en %, une petite en bulletins.

Le nombre de bulletins seul ne dit rien : certains cantons publient le même
chiffre pour tous les objets (Berne, Genève, Vaud…), d'autres un chiffre par
objet, où un votant peut n'avoir glissé qu'un bulletin. D'où la comparaison
de chaque commune à elle-même.

- **Orange** : un écart sur une mesure — vote (χ² au-dessus de 20, ou un
  objet à plus de 5 σ) ou bulletins (plus de 8 σ de son habitude).
- **Rouge** : un très gros écart sur une mesure (vote à plus de 10 σ,
  bulletins à plus de 20 σ), ou un écart sur les deux. Une correction simple
  compte comme la seconde mesure quand elle efface l'écart de vote (χ² ramené
  sous 6), ou le fait passer d'au moins 3 σ à moins de 1,5 σ.
- **Vert** : le reste.

Hystérésis : une commune signalée ne retombe que sous des seuils plus bas
(`SORTIE` dans le code), sinon elle clignoterait au gré des communes qui
arrivent. Si ses chiffres changent dans le fichier fédéral, on repart de
zéro : une commune corrigée redevient verte.

Rejoué sur une base reconstruite à partir des sources publiques (historique
STAT-TAB depuis le 30.11.2014, fichier fédéral du 29.09.2026, pas encore
corrigé) : **4 rouges, exactement les quatre communes confirmées**.
Verzasca, Büttenhardt et Ursins par le vote et sa correction ; Wolfhalden par
ses bulletins (12,7 % d'écart, d'habitude 1,3 %) et la correction 275 → 175,
qui ramène son vote de 3,3 σ à presque rien. Orange : Saint-Saphorin,
Marchissy et cinq autres par le vote ; Guttannen, Biel-Benken et Allschwil
par les bulletins.

Une première version ajoutait l'écart de bulletins, mesuré en √bulletins,
au χ² du vote : dix-sept communes passaient au rouge à tort, des grandes
communes à l'écart de bulletins banal (Zurich, Dübendorf) qu'une
« correction » d'un chiffre absorbait.

La note libre de chaque commune s'écrit dans l'admin Django, à la main ou par
un agent ; le calcul n'y touche jamais.

## Le résultat du 27 septembre 2026 : 4 sur 4

Les quatre communes où une correction simple expliquait tout ont été
confirmées :

| Commune | Erreur prédite | χ² avant → après | Confirmation |
|---|---|---|---|
| Wolfhalden (AR) | 275 oui saisis pour 175 | 554 → 0,9 | la commune, puis le fichier fédéral corrigé |
| Verzasca (TI) | oui et non inversés sur un objet | 108 → 0,9 | la commune |
| Büttenhardt (SH) | oui et non inversés sur un objet | 43 → 2,2 | le fichier fédéral corrigé |
| Ursins (VD) | résultats des deux objets intervertis | 24 → 1,0 | recomptage par le bureau |

Le terme des bulletins compte : Wolfhalden n'avait qu'un écart modeste en %
de oui (3,5 σ), c'est l'incohérence de ses bulletins entre les deux objets
(673 contre 771) qui l'a trahie. À l'inverse, des communes à 8 σ sans
correction simple (Saint-Saphorin, Marchissy) restent des pistes ouvertes.

## L'historique a été vérifié

Les 103 objets × 2 122 communes de l'historique réel (depuis le 30.11.2014)
ont été confrontés au fichier fédéral de chaque date : **103 664 lignes, zéro
inversion oui/non**. Seul écart systématique : quatre communes (Zäziwil,
Gurmels, Kriegstetten, Brugg) portent des totaux supérieurs à l'officiel,
parce que le cube STAT-TAB les exprime dans leur périmètre d'après fusion.
Inutile de relancer une chasse aux erreurs sur l'historique : le détecteur
sert le jour J.

## Ce qu'une source concordante ne prouve pas

Canton, OFS et données de presse reprennent tous le **même procès-verbal
communal**. Une erreur de saisie initiale est donc cohérente partout, et
retrouver le même chiffre ailleurs ne la dément pas. Seuls un recomptage ou
le procès-verbal de la commune tranchent. Exemple : Val-d'Illiez (VS),
question subsidiaire du 8 mars 2026, −10,8 σ, chiffres identiques au fédéral,
au cantonal et à la presse — toujours suspect, jamais tranché.

Source cantonale utile pour le Valais : l'API publique de publication des
résultats, `https://vework-public.vs.ch/data/publication` (portail :
`https://vework-public.vs.ch/app/publication/fr/<JJ-MM-AAAA>/issues`), JSON
sans authentification.
