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

1. **Profil de commune par ACP** (`scripts/populate_pca.py`). On construit la matrice
   commune × objet des % de oui sur **55 votations passées** (`ResultatCommunalHistorique`), et on la
   réduit à **6 composantes principales** (`sklearn`), stockées dans `PCAResult`.
   Une commune qui n'a pas exactement 55 `ResultatCommunalHistorique` est écartée de l'ACP.
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

À noter : `scripts/run_extrapolation.py` **écrit les valeurs extrapolées dans les
lignes `ResultatCommunalEnCours`** des communes non dépouillées (tout en laissant
`comptabilise=False`). C'est ce qui permet aux cartes d'afficher toute la Suisse —
mais les cartes **ne distinguent donc pas visuellement réel et estimé**.

---

## Applications Django

| App | Rôle |
|---|---|
| `scrutin` | Cœur métier : tous les modèles, la logique d'extrapolation, la vue d'accueil, le CSS et le logo. |
| `pca` | Modèle `PCAResult` (6 coordonnées par commune) + vue nuage de points ACP colorée par langue. |
| `carte` | `carte/API.py` : cartes choroplèthes Plotly sur le GeoJSON communal. |
| `page_statique` | Pages éditables en base (Méthodes, Contact), servies par une route attrape-tout `path("<str>", …)`. |

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

`peupler_demo` fabrique 2 141 communes réelles (nom, numéro OFS, district, canton
lus dans `data/K4voge_*.geojson`), 55 votations historiques et une soirée de
dépouillement en cours — le tout fictif, déterministe, hors-ligne, et **sans
scipy ni scikit-learn**. Les votes suivent un profil latent par commune
(urbain/rural, latin/alémanique), et les petites communes dépouillent en premier :
l'ACP y trouve une vraie structure et l'extrapolation a un vrai biais à corriger.

---

## Pipeline de données

Les scripts s'exécutent via **django-extensions** :
`python manage.py runscript <nom>` (depuis la racine du repo).

Amorçage, **dans cet ordre** (chaque étape dépend de la précédente) :

```
populate_commune          # cantons, districts, communes
import_metadata_commune   # langue, degré d'urbanisation
populate_voix             # 55 votations historiques  (⚠ supprime tous les SujetVote)
set_nb_voix_commune       # Commune.nb_voix = électeurs de la dernière votation
populate_pca              # ACP → PCAResult          (⚠ supprime tous les PCAResult)
add_initial_scrutin_en_cours --script-args <json_du_scrutin>   # lignes vides du jour J
```

Puis, en boucle le jour du scrutin :
`update_scrutin_en_cours --script-args <json_courant> <json_precedent>` →
`run_extrapolation`. C'est ce que fait `download_data.sh`, qui dérive URL et noms
de fichiers de `DATE_SCRUTIN`.

`update_scrutin_en_cours` ne réimporte que les communes **nouvellement** dépouillées
(différence entre deux instantanés JSON) — l'import complet était trop lent. Une
commune n'est reprise que lorsqu'elle est rentrée pour **tous** les objets du
scrutin.

Les deux imports du jour J sont **idempotents** : `add_initial_scrutin_en_cours`
sème les lignes vides (`get_or_create`), `update_scrutin_en_cours` les remplit
(`update_or_create`). Il n'y a donc jamais qu'une ligne `ResultatCommunalEnCours` par
commune et par objet — l'invariant n'est pas garanti par la base, seulement par
le code et `tests/test_import_idempotent.py`.

`create_fake_json_input --script-args <json_du_scrutin> [<sortie>]` fabrique un JSON
de test en rejouant d'anciens résultats sur 5 % des communes tirées au hasard :
c'est le moyen de tester sans attendre un vrai dimanche de votation.

### Source des données
JSON open data de la Confédération (`app-prod-static-voteinfo.s3…/ogd/`), format
alémanique : `vorlagen`, `kantone`, `gemeinden`, `jaStimmenAbsolut`,
`neinStimmenAbsolut`, `anzahlStimmberechtigte`, `eingelegteStimmzettel`.
Les communes sont appariées par **numéro OFS** (`geoLevelnummer`).

---

## Déploiement (`download_data.sh`)

Approche volontairement rustique : une boucle `while true` qui, à chaque tour,
télécharge le JSON fédéral, met à jour la base, relance l'extrapolation, **puis
aspire tout le site Django avec `wget --recursive` pour en faire un mirroir HTML
statique** copié dans `/srv/html/` (servi par Apache).

Conséquence importante : **la production ne fait pas tourner Django**. Le site en
ligne est une photo statique régénérée en boucle — ce qui le rend insensible à la
charge un soir de votation. Toute modification doit rester compatible avec cette
aspiration (pas de contenu dépendant d'une requête utilisateur, pas de POST).

Le script contient des valeurs codées en dur : `192.168.1.20:8000`, `/srv/html/`,
`~/env/django/bin/activate`, et les noms `votation_septembre_2022_*`.

---

## Pièges connus

**Données**
1. **Deux racines de données différentes.** Les scripts lisent `../data/…` (hors du
   repo : `donnee_federale_v3.txt`, `communes/`, `votation_septembre_2022_*.json` —
   **rien de tout ça n'est versionné**), alors que `carte/API.py` lit `data/…`
   (dans le repo). Ne pas les confondre.

**Valeurs codées en dur** — **corrigées** (jalon 3, tâche B2)
2. Le `55` de `ScrutinAPI` était en dur à deux endroits → `nb_sujets_historiques()`,
   déduit des `ResultatCommunalHistorique`. Une commune à l'historique incomplet est toujours écartée de
   l'ACP, mais avec un avertissement (le seuil de couverture est l'affaire de la
   Partie 6).
3. `update_scrutin_en_cours.get_new_commune` bouclait sur `range(2)` : il ignorait
   les objets au-delà du deuxième et plantait sur un scrutin à objet unique.
4. Les chemins `votation_septembre_2022_*` sont devenus des arguments
   (`--script-args`), et `download_data.sh` dérive URL et fichiers de
   `DATE_SCRUTIN`.

**Bugs latents repérés à la lecture** — **corrigés** (jalon 2, tâche A4)
5. `Commune.get_last_nb_electeur_slow` triait une liste jetable (tri sans effet)
    → `order_by('-sujet_vote__date').first()`.
6. `add_initial_scrutin_en_cours` / `update_scrutin_en_cours` /
    `create_fake_json_input` : le `except` autour de `get_unique_commune_by_ofs`
    ne faisait pas `continue` — la boucle réutilisait la `commune` de
    l'itération précédente.
7. `ScrutinAPI.getVotationMatrixWithMetaInfo` utilisait `voixs` après la boucle
    (variable qui fuit) et appelait `Warning(…)` au lieu de `warnings.warn(…)`.
8. `populate_voix.add_foreigner` testait `len(districts)` au lieu de
    `len(communes)` ; le message d'erreur des sujets en double référençait une
    variable inexistante (`commune.Canton`).

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
graphiques.py  [I]  histogramme(vue) -> div HTML       (aucun ORM)
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

`peupler_demo` construit une base **à l'échelle réelle** (~2 130 communes, tirées du
GeoJSON déjà présent dans `data/`), avec un historique de votes fictif structuré par
profil latent — l'ACP y trouve donc une vraie structure. Graine fixe, aucun
téléchargement, tourne hors-ligne.

**La base est SQLite partout, dev comme prod** (un seul écrivain, ~120 000 lignes,
sauvegarde = copie du fichier). Pas de Postgres, pas de `psycopg`.

### Deux agents en parallèle

Les deux voies existent aussi comme **agents Claude**, définis dans
`.claude/agents/` : `moteur` et `interface`. Chacun a la liste de ses fichiers,
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

## Conventions

Domaine et modèles en **français** (`Commune`, `SujetVote`, `ResultatCommunalHistorique`, `nombre_oui`,
`requete`), messages de commit et quelques helpers en anglais. Garder le français
pour tout ce qui touche au métier et à l'interface.

Branches : `master`, plus les préfixes `moteur/` et `interface/` (voir ci-dessus).
Les anciennes branches nominatives `Frederic` et `Laurence` sont abandonnées — le
sujet compte plus que l'auteur.
