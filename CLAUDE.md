# election — Politiques.ch

Site Django qui **projette en direct le résultat des votations fédérales suisses**
le dimanche de scrutin : à partir des communes déjà dépouillées, il extrapole les
communes manquantes et affiche le % de oui attendu, avec des cartes choroplèthes par
objet.

Titre public du site : « Projections de votations & autres analyses de politique
helvétique » (`templates/base.html`).

---

## La méthode d'extrapolation (le cœur du projet)

L'idée : les communes suisses ont des profils de vote stables. On les caractérise par
leur historique, puis on prédit les communes non dépouillées à partir de celles qui
le sont déjà.

1. **Profil de commune par ACP** (`manage.py populate_pca`). On construit la matrice
   commune × objet des % de oui sur les **votations passées** (`ResultatCommunalHistorique` :
   55 dans la base fictive, tout ce que `importer_historique --depuis` a chargé
   en réel), et on la réduit à **6 composantes principales** (`sklearn`),
   stockées dans `PCAResult`. Une commune à qui il manque un seul objet
   historique est écartée de l'ACP.
2. **Régression le jour J** (`scrutin/extrapolation.py`). Sur les communes déjà
   comptabilisées, on ajuste par moindres carrés — **pondérés par le nombre de
   bulletins rentrés** — un modèle linéaire `% oui ≈ Σ aᵢ·composanteᵢ + b`
   (7 paramètres). On ajuste **le même modèle séparément pour la participation**.
3. **Projection.** Pour chaque commune manquante, on applique les deux modèles, et on
   estime son nombre de votants via `electeur_election_precedente`. On somme, on
   ajoute au dépouillement confirmé, et on obtient le % de oui final projeté plus
   l'`avance` (part du dépouillement déjà couverte).

Garde-fou : sous **7 communes dépouillées**, `get_extrapolation` renvoie `0.5, 0.5, 0`
plutôt qu'un ajustement sur trop peu de points.

Une commune sans profil ACP ne fait jamais tomber la projection : déjà
dépouillée, ses bulletins comptent mais elle ne sert pas à ajuster le modèle ;
pas encore rentrée, elle est projetée avec le profil moyen de son district. Le
cas est courant — une commune qui se met à publier ses résultats séparément n'a
pas d'historique, donc pas de profil.

À noter : `manage.py run_extrapolation` **écrit les valeurs extrapolées dans les
lignes `ResultatCommunalEnCours`** des communes non dépouillées (tout en laissant
`comptabilise=False`). C'est ce qui permet aux cartes d'afficher toute la Suisse —
mais les cartes **ne distinguent donc pas visuellement réel et estimé**.

---

## Applications Django

| App | Rôle |
|---|---|
| `scrutin` | Cœur métier : tous les modèles, la logique d'extrapolation, la vue d'accueil, le CSS et le logo. |
| `pca` | Modèle `PCAResult` (6 coordonnées par commune). `donnees.py` (contrat de vue) et `figures.py` : pages `/nuage-acp` (communes) et `/objets-acp` (cercle des corrélations), chacune avec deux cartes des axes choisis. Corrélations et part de variance calculées à la volée. Points nommés d'office dans `figures.py` ; nuage et cartes se répondent au survol et au clic (`nuage.js`). Pages pensées pour l'ordinateur. Le PDF lié, `pca/static/pca/axes_acp.pdf`, est une copie de `doc/axes_acp.pdf` (branche `moteur/analyse-axes-acp`). |
| `carte` | `carte/API.py` : cartes choroplèthes Plotly sur le fond communal — résultats du jour (`/cartes`) et axes de l'ACP (`figure_carte_acp` : les six axes dans une seule figure, que `carte_acp.js` trace deux fois à côté des nuages). Le fond n'est **pas** incrusté dans les figures : c'est un fichier statique (`carte/static/carte/communes.geojson`, 5,8 Mo), que plotly.js télécharge une fois pour toutes les cartes de la page. `manage.py generer_contours` le fabrique. |
| `page_statique` | Pages du menu (aujourd'hui : Contact), écrites dans `page_statique/contenus/` et recopiées en base par `manage.py peupler_pages`, servies par la route attrape-tout `path("<slug:url>", …)` (404 si absente). **Ce sont aussi les onglets du menu** : le context processor `page_statique.context_processors.menu` les expose à tous les gabarits, et `base.html` boucle dessus. Ajouter une page en base ajoute donc un onglet, sans toucher au HTML. |

### Modèles (`scrutin/models.py`)
`Canton` → `District` → `Commune` ; `SujetVote` (un objet de votation) ;
**`ResultatCommunalHistorique`** = résultat *historique définitif* commune × objet ; **`ResultatCommunalEnCours`** =
résultat *du jour*, avec `comptabilise` et `electeur_election_precedente` ;
`Extrapolation` = un instantané horodaté de la projection (la vue affiche le dernier).

La distinction `ResultatCommunalHistorique` / `ResultatCommunalEnCours` est structurante : `ResultatCommunalHistorique` alimente l'ACP,
`ResultatCommunalEnCours` est réécrit toutes les quelques minutes le jour du scrutin.

---

## Mise en route

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements/dev.txt
cp .env.example .env            # DEBUG=1 suffit en local
python manage.py migrate        # SQLite, aucune installation requise
python manage.py peupler_demo   # base fictive à l'échelle réelle
python manage.py runserver
```

`peupler_demo` sème aussi les pages du menu, via `peupler_pages` — la même
commande que sur une base réelle : sans elles, un clone frais aurait des
onglets en 404.

`peupler_demo` fabrique les 2 110 communes réelles (nom, numéro OFS, district, canton
lus dans `data/agvch_niveaux_*.csv`, le même référentiel que `populate_commune`
— la base fictive porte donc exactement les communes du fond de carte),
55 votations historiques et une soirée de
dépouillement en cours — le tout fictif, déterministe, hors-ligne, et **sans
scipy ni scikit-learn**. Les votes suivent un profil latent par commune
(urbain/rural, latin/alémanique), et les petites communes dépouillent en premier :
l'ACP y trouve une vraie structure et l'extrapolation a un vrai biais à corriger.

---

## Pipeline de données

Le pipeline est fait de **management commands Django** (`scrutin/management/commands/`,
`pca/management/commands/`) : `python manage.py <nom> [args]`, `--help` pour les arguments.

Amorçage, **dans cet ordre** (chaque étape dépend de la précédente) :

```
populate_commune          # cantons, districts, communes (⚠ supprime tous les Canton, donc tout le reste en cascade)
import_metadata_commune   # langue, degré d'urbanisation
importer_historique       # votations passées depuis STAT-TAB (réseau, ⚠ crée les pseudo-communes 9xxx)
set_nb_voix_commune       # Commune.nb_voix = électeurs de la dernière votation
populate_pca              # ACP → PCAResult          (⚠ supprime tous les PCAResult)
add_initial_scrutin_en_cours <json_du_scrutin>   # lignes vides du jour J
```

Les deux premières étapes lisent le **même** fichier : `data/agvch_niveaux_2026-01-01.csv`,
export `levels` du répertoire officiel des communes de l'OFS (API AGVCH, sans
clé), versionné dans le dépôt. Une ligne par commune, la hiérarchie déjà jointe
(`BfsCode`, `DistrictId`, `CantonId`) plus la langue et le degré d'urbanisation.
Les deux commandes gardent le chemin en argument optionnel ; l'URL de
rafraîchissement est dans leurs docstrings.

Puis, en boucle le jour du scrutin :
`update_scrutin_en_cours <json_precedent> <json_courant>` →
`run_extrapolation`. C'est ce que fait `download_data.sh`, qui dérive URL et noms
de fichiers de `DATE_SCRUTIN`.

`update_scrutin_en_cours` ne réimporte que les communes **nouvellement** dépouillées
(différence entre deux instantanés JSON) — l'import complet était trop lent. Une
commune n'est reprise que lorsqu'elle est rentrée pour **tous** les objets du
scrutin.

Les deux imports du jour J sont **idempotents** : `add_initial_scrutin_en_cours`
sème les lignes vides (`get_or_create`), `update_scrutin_en_cours` les remplit
(`update_or_create`). Il n'y a donc jamais qu'une ligne `ResultatCommunalEnCours` par
commune et par objet — invariant **garanti par la base** (contrainte
`une_ligne_par_commune_et_objet`, migration `scrutin/0002`).

`create_fake_json_input <json_du_scrutin> [<sortie>]` fabrique un JSON
de test en rejouant d'anciens résultats sur 5 % des communes tirées au hasard :
c'est le moyen de tester sans attendre un vrai dimanche de votation.

### Source des données
**Jour J** : JSON open data de la Confédération (`app-prod-static-voteinfo.s3…/ogd/`), format
alémanique : `vorlagen`, `kantone`, `gemeinden`, `jaStimmenAbsolut`,
`neinStimmenAbsolut`, `anzahlStimmberechtigte`, `eingelegteStimmzettel`.
Les communes sont appariées par **numéro OFS** (`geoLevelnummer`).

**Historique** : cube STAT-TAB de l'OFS `px-x-1703030000_101`, API PX-Web JSON
sans clé, **déjà harmonisé sur les communes actuelles** — une commune fusionnée
porte les voix de ses prédécesseurs, l'appariement par numéro OFS suffit. Les
codes d'objet du cube sont les `vorlagenId` du jour J. `importer_historique`
charge par lots de 10 : au-delà, l'OFS répond 403.

**Fond de carte** : `swissBOUNDARIES3D` de swisstopo, millésime 2026, en
GeoPackage LV95 — du SQLite, donc lu sans dépendance. `manage.py
generer_contours <gpkg> <topojson>` en tire `carte/static/carte/communes.geojson`
(les 2 110 communes, ~140 sommets chacune) et `lacs.geojson`, tous deux
committés. La commande ne resert qu'au changement de millésime ; les deux URL
sources sont dans son docstring, avec les deux API où retrouver le millésime
suivant.

Trois points qui expliquent le reste :
- La simplification (Douglas-Peucker, 25 m) **garde la topologie** : une
  frontière partagée est simplifiée une seule fois, sinon un liseré blanc
  apparaîtrait entre communes voisines.
- Les **lacs sont un fichier à part**, peint par-dessus les communes : dans
  swissBOUNDARIES3D, une commune riveraine s'étend jusqu'au milieu de l'eau.
- L'appariement se fait par **numéro OFS** (`properties.vogeId`), comme partout
  ailleurs ; le nom affiché au survol vient du fichier de contours lui-même.

---

## Déploiement

**La production fait tourner Django**, derrière un cache nginx. Le cache, le
script du jour J et le timer systemd sont versionnés dans `deploiement/` et
décrits pas à pas dans [`DEPLOIEMENT.md`](DEPLOIEMENT.md). Le déroulé d'un
dimanche, à cocher, est dans [`CHECKLIST_JOUR_J.md`](CHECKLIST_JOUR_J.md) ; il
commence par une répétition générale (`deploiement/repetition_generale.sh`) qui
rejoue une soirée entière sur une copie de la base.

Contrainte qui demeure : le site doit rester **cachable**, donc sans contenu
dépendant du visiteur et sans POST. Seule exception : le formulaire de contact,
qui poste vers `/contact/envoyer` (jamais en cache, limité par nginx) et envoie
par la boîte `contact@politiques.ch` (DEPLOIEMENT.md, § 7 ter). La page Contact
reste identique pour tous : ni jeton CSRF (`csrf_exempt`), ni cookie.

### Le conteneur (C1)

`Dockerfile` + `compose.yaml`, **un seul service** : `web`, gunicorn qui sert
Django. Ni base de données ni proxy — SQLite est un fichier et c'est le serveur
web de l'hôte qui garde le trafic public. Le port n'est publié que sur
`127.0.0.1`.

La même image sert à tout : elle contient la pile scientifique, donc les
commandes du pipeline s'exécutent dedans.

```bash
docker compose up -d --build
docker compose run --rm web python manage.py run_extrapolation
```

Deux points de conception qui expliquent le reste :

- **`./var` est monté sur `/app/var`**, donc au même chemin relatif des deux
  côtés. `var/scrutins/votation_20260927_3.json` désigne le même fichier sur
  l'hôte et dans le conteneur : `download_data.sh` passe ses chemins tels quels
  à des commandes qui tournent, elles, dans le conteneur. C'est aussi là que vit
  la base, pour que la sauvegarde reste une copie de fichier.
- **whitenoise** est dans les middlewares : avec `DEBUG=0`, Django refuse de
  servir `/static/`, et le site sortirait sans CSS ni logo. `collectstatic` est
  lancé à la construction de l'image.

nginx, HTTPS et le timer vivent sur l'hôte, pas dans un conteneur : le
conteneur ne publie son port que sur `127.0.0.1`.

---

## Pièges connus

**Valeurs codées en dur** — **corrigées** (jalon 3, tâche B2)
1. Le `55` de `ScrutinAPI` était en dur à deux endroits → `nb_sujets_historiques()`,
   déduit des `ResultatCommunalHistorique`. Une commune à l'historique incomplet est toujours écartée de
   l'ACP, mais avec un avertissement (le seuil de couverture est l'affaire de la
   Partie 6).
2. `update_scrutin_en_cours.get_new_commune` bouclait sur `range(2)` : il ignorait
   les objets au-delà du deuxième et plantait sur un scrutin à objet unique.
3. Les chemins `votation_septembre_2022_*` sont devenus des arguments, et `download_data.sh` dérive URL et fichiers de
   `DATE_SCRUTIN`.

**Bugs latents repérés à la lecture** — **corrigés** (jalon 2, tâche A4)
4. `Commune.get_last_nb_electeur_slow` triait une liste jetable (tri sans effet)
    → `order_by('-sujet_vote__date').first()`.
5. `add_initial_scrutin_en_cours` / `update_scrutin_en_cours` /
    `create_fake_json_input` : le `except` autour de `get_unique_commune_by_ofs`
    ne faisait pas `continue` — la boucle réutilisait la `commune` de
    l'itération précédente.
6. `ScrutinAPI.getVotationMatrixWithMetaInfo` utilisait `voixs` après la boucle
    (variable qui fuit) et appelait `Warning(…)` au lieu de `warnings.warn(…)`.

Les `except:` nus ont été remplacés par des exceptions ciblées partout.

## Tests, lint et CI

```bash
pytest                 # toute la suite (~10 s), hors-ligne
pytest -m "not lent"   # sans les tests qui peuplent la base complète
ruff check .           # lint
```

`tests/test_extrapolation.py` fixe le cœur mathématique sur des données
synthétiques **dont le résultat est connu analytiquement** (le modèle affine
qui a engendré les données doit être retrouvé par le fit) ; `tests/test_pipeline.py`
enchaîne `peupler_demo` → ACP → extrapolation et vérifie que la projection
**corrige** le biais du dépouillement partiel, en plus de garder un œil sur le
« 55 » codé en dur.

La configuration vit dans `pyproject.toml` : sans elle, ruff prenait la
configuration globale de chaque machine et les deux voies ne voyaient pas les
mêmes erreurs. Le jeu de règles est volontairement modeste (`E4`, `E7`, `E9`,
`F`, `I`) — élargir d'un coup noierait les vraies erreurs sous du style.

`election/settings_test.py` active `DEBUG` avant d'importer les réglages : la
suite tourne donc depuis un clone frais, sans `.env`. GitHub Actions rejoue
lint + tests sur chaque PR.

## Travail à deux — deux voies parallèles

Le projet est repris à deux, **chacun son clone et sa branche**. La réflexion sur
l'évolution est commune ; la réalisation est répartie en deux voies :

| | **Voie M — Moteur** | **Voie I — Interface** |
|---|---|---|
| Domaine | maths, backend, infra | design, frontend, données |
| Branches | `moteur/…` | `interface/…` |
| Fichiers | `extrapolation.py`, `donnees.py`, `models.py`, `pca/`, migrations, management commands, `settings.py`, Docker, CI | `templates/`, `*/static/`, `charte.py`, `graphiques.py`, `carte/figure.py`, `maquette/` |

**Règle : on ne modifie pas la zone de l'autre sans la lui demander.** Si la voie I
a besoin d'une donnée supplémentaire, elle la demande — elle ne va pas la chercher
elle-même dans l'ORM.

### La couture données / présentation

Le point de contact est un **contrat de vue** : un dict simple, sérialisable en
JSON, produit par la voie M et consommé par la voie I.

```
donnees.py     [M]  construire_vue_accueil() -> dict   (aucun Plotly)
graphiques.py  [I]  accueil(vue) -> contexte du gabarit (aucun ORM)
views.py    [commun] assemble les deux — doit rester minuscule
```

Ce n'est pas un fichier chargé à l'exécution : juste la forme du dict, figée par
`tests/test_contrat.py` qui tourne sur la base fictive. Si la voie M change la forme
sans prévenir, la CI casse. C'est le garde-fou anti-dérive, et le seul fichier
qu'on édite à deux.

### Deux jeux de données, un seul chemin de code

Pas de mode maquette et pas de branche `if` dans les vues : le site tourne toujours
de la même façon, **seule la base change**.

| Jeu | Comment | Pour qui |
|---|---|---|
| **Fictif** | `manage.py peupler_demo` | tout le monde, au quotidien |
| **Réel** | pipeline d'import (historique + JSON du jour J) | voie M : projections réelles, dry run, prod |

`peupler_demo` construit une base **à l'échelle réelle** (2 110 communes, tirées du
référentiel déjà présent dans `data/`), avec un historique de votes fictif structuré par
profil latent — l'ACP y trouve donc une vraie structure. Graine fixe, aucun
téléchargement, tourne hors-ligne.

**La base est SQLite partout, dev comme prod** (un seul écrivain, ~120 000 lignes,
sauvegarde = copie du fichier). Pas de Postgres, pas de `psycopg`.

### Deux agents en parallèle

Les deux voies existent aussi comme **agents Claude**, définis dans
`.claude/agents/` : `moteur` et `interface` — plus `passeur`, qui fait
traverser le design de la branche `maquette` (voir plus bas). Chacun a la liste de ses fichiers,
ses frontières explicites, et l'interdiction de toucher la zone de l'autre.

- **Un agent par voie, un clone (ou un worktree) par agent.** Deux agents dans le
  même répertoire de travail se marcheraient dessus sur l'index git.
- L'agent `interface` travaille sur la base fictive : `peupler_demo` puis
  `runserver`. Ni pile scientifique, ni données réelles, ni réseau.
- **Le contrat est le seul point de rendez-vous.** Un agent qui a besoin d'un
  champ absent ne va pas le chercher lui-même : il le demande, et le contrat
  (plus son test) est mis à jour des deux côtés.
- Les tâches sont étiquetées **[M]**, **[I]** ou **[2]** dans le plan — un agent
  ne prend que les siennes, et **[2]** signale ce qui se décide à deux.

Détail complet et découpage des tâches par voie : [`PLAN_MODERNISATION.md`](PLAN_MODERNISATION.md) Partie 0.

### Refonte graphique : la maquette d'abord, sur sa propre branche

Le design ne part pas d'une charte abstraite : on itère sur des **pages HTML
statiques** qui embarquent les **vraies figures Plotly en JSON** — produites
par les mêmes fonctions que le site, jamais dessinées à la main — et un bloc
de réglages `charte.js`. Une fois une variante retenue, la charte CSS et
`charte.py` en sont *extraites*, puis transposées dans les gabarits Django.

Tout ce chantier vit sur la branche **`maquette`**, qui n'est **jamais
fusionnée dans `master`** : c'est un travail de conception, utile une fois,
qui encombrerait la branche principale pour des années. La synchronisation va
dans un seul sens, `master` → `maquette`. Le passage en production est une
**réécriture**, confiée à un troisième agent, `passeur`, seul à lire les deux
branches. Détail : Partie 7 du plan (7.0 pour les branches, 7.4 pour le
passage).

## Conventions

Domaine et modèles en **français** (`Commune`, `SujetVote`, `ResultatCommunalHistorique`, `nombre_oui`,
`requete`), messages de commit et quelques helpers en anglais. Garder le français
pour tout ce qui touche au métier et à l'interface.

Branches : `master`, plus les préfixes `moteur/` et `interface/` (voir ci-dessus).
Les anciennes branches nominatives `Frederic` et `Laurence` sont abandonnées — le
sujet compte plus que l'auteur.
