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
   communes voisines, pour écarter un effet régional réel.

Une correction qui ramène le χ² près de zéro est un signal fort ; un écart
élevé sans correction simple qui l'explique est le plus souvent un vrai vote
singulier.

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
