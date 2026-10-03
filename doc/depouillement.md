# Comment les communes publient le jour J

Ce qu'on a appris du fichier fédéral en le suivant toutes les cinq minutes,
pendant le scrutin du 27 septembre 2026. Ce qui en découle pour le code est
déjà dans `update_scrutin_en_cours`.

## Une commune n'est dépouillée que si `gebietAusgezaehlt` le dit

Le fichier fédéral (`sd-t-17-02-<date>-eidgAbstimmung.json`) porte, pour
chaque commune et chaque objet, un booléen `gebietAusgezaehlt`. **C'est le
seul critère fiable.** Plusieurs communes publient des voix avant la fin de
leur dépouillement : `jaStimmenAbsolut` est alors rempli alors que le compte
n'est pas terminé.

## Deux familles de résultats partiels

Comparaison de chaque publication partielle au résultat final, le 27.09.2026
(écart en points de % de oui) :

| Commune | Part des voix publiées | Écart au final |
|---|---|---|
| Zurich | 5 % | **+10,3** (neutralité), −1,8 (alimentation) |
| Zurich | 15 à 90 % | entre −1,1 et +1,0 |
| Winterthour | 34 à 65 % | **+3,7 / +3,8** et **−2,6 / −2,3** |
| Winterthour | 89 % | +0,7 / −0,6 |
| Bâle, Riehen, Bettingen, Bâle-étranger | 96 à 99 % | ≤ 0,8, le plus souvent ≤ 0,2 |

- **Zurich et Winterthour publient par tranches** (vraisemblablement par
  quartier ou bureau) : chaque palier est une portion géographique de la
  ville, pas un échantillon. Les premiers paliers sont franchement biaisés, et
  la participation y est sous-estimée (36 % au premier palier zurichois, 50 %
  à la fin).
- **Bâle-Ville publie d'abord le vote par correspondance**, vers 12 h 10 : 96 à
  99 % des voix, à moins d'un point du final. Ces communes ne passent
  pourtant `gebietAusgezaehlt` qu'à 15 h 35. Le critère strict s'en prive
  pendant plus de trois heures — piste ouverte dans `PLAN.md`.

## Des communes corrigées après coup

Trois communes ont changé leurs chiffres **après** avoir été déclarées
dépouillées, dans l'heure qui a suivi : +67 bulletins pour l'une, −10 non pour
une autre, +7 bulletins pour la troisième. Et le fichier fédéral lui-même est
corrigé les jours suivants : celui du 30.09.2026 reprenait une quarantaine de
lignes (oui/non inversés, inscrits gonflés dans une quinzaine de communes
vaudoises, bulletins).

D'où le réimport complet à chaque tour : une correction est reprise au tour
suivant. Il prend environ 3 s pour tout un scrutin. Après le scrutin, réimporter
le fichier fédéral corrigé.

## Ce que le fichier ne dit pas

- **Aucune heure par commune.** Seul le fichier entier porte un `timestamp`,
  et il est écrasé en place : l'historique intra-journée n'existe que si on
  l'archive soi-même. C'est ce que fait `download_data.sh`, qui garde chaque
  instantané sous `var/scrutins/`. Les noms de fichiers sont en **UTC**
  (heure suisse = UTC + 2 en été, + 1 en hiver).
- Seule exception connue : `kommunale_resultate_<aaaa_mm_jj>.json` (le
  service temps réel des objets communaux de ZH, AG, GR, SZ, ZG) porte un
  `timestamp` à la minute par commune. Une trentaine de dates archivées depuis
  2023, environ 2 400 lignes : de quoi mesurer l'ordre d'arrivée réel.
- Les deux hôtes `app-prod-static-voteinfo.s3.eu-central-1.amazonaws.com` et
  `ogd-static.voteinfo-app.ch` servent le même fichier.

## Hypothèse de travail : le premier affichage vers 25 %

Vers midi, environ un quart du dépouillement est déjà publié. Les variantes du
modèle s'évaluent donc à 25 % d'avance, pas à 5 %. **Hypothèse posée, pas
encore mesurée** : les fichiers horodatés ci-dessus permettraient de la
vérifier. Le 27.09.2026, la projection (avec le bon critère de dépouillement)
était à −0,23 et −0,15 point du résultat final dès 12 h 05, à 26 % d'avance.
