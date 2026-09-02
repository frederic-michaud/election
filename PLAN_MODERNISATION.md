# Plan de modernisation — Politiques.ch

*Établi le 24 août 2026. Document de travail : cocher / annoter au fil de l'eau.*

> **Règle** : une tâche du plan qui est terminée se coche **dans la même PR**
> que le travail qui la termine (ou dans un commit `plan: …` juste après si
> le travail dépasse une seule tâche). Ne pas laisser ça pour plus tard — le
> jalon 1 (A1–A3) a été fait sans jamais toucher ce fichier, et le plan a
> menti pendant plusieurs jours sur ce qui restait à faire.

## Décisions actées

- **Architecture** : on garde Django, modernisé (Django 5.2 LTS, Python 3.12+).
- **Priorité n°1** : assainir la base avant toute nouvelle fonctionnalité.
- **Hébergement** : VPS Infomaniak, comme avant (Docker Compose envisagé).
- **Base de données** : **SQLite partout**, dev comme prod. Postgres est
  surdimensionné ici (voir Partie 0).
- **Périmètre à terme** : intégrer les élections (méthode reports de voix du repo
  `extrapolation_politique`) en plus des votations — en phase finale.
- **Organisation** : deux personnes, deux voies parallèles, deux clones (Partie 0).

---

## Partie 0 — Organisation du travail à deux

### Les deux voies

| | **Voie M — Moteur** | **Voie I — Interface** |
|---|---|---|
| Domaine | maths, backend, infra | design, frontend, données |
| Contenu | extrapolation, ACP, modèles, pipeline, Docker, CI | charte graphique, templates, figures Plotly, sources de données |
| Préfixe de branche | `moteur/…` | `interface/…` |

La **réflexion sur l'évolution se fait en commun** : décisions d'architecture,
forme du contrat (ci-dessous), méthode statistique, priorités. Seule la
*réalisation* est répartie.

### Répartition des fichiers

| Chemin | Voie |
|---|---|
| `scrutin/extrapolation.py`, `scrutin/donnees.py`, `pca/` | **M** |
| `scrutin/models.py`, migrations, management commands | **M** |
| `election/settings.py`, `Dockerfile`, `compose.yaml`, CI | **M** |
| `carte/donnees.py` | **M** |
| `templates/`, `*/static/` (CSS, JS, logo) | **I** |
| `scrutin/charte.py`, `scrutin/graphiques.py`, `carte/figure.py` | **I** |
| `*/views.py` | **commun** — doit rester minuscule (voir couture) |
| `tests/test_contrat.py` | **commun** — fige la forme du contrat |
| `CLAUDE.md`, `PLAN_MODERNISATION.md` | **commun** |

**Règle** : on ne modifie pas la zone de l'autre sans le lui demander. Si la
voie I a besoin d'un champ supplémentaire, elle le demande à la voie M *et on
met à jour le contrat ensemble* — on ne va pas le chercher soi-même dans l'ORM.

### La couture : un contrat « vue » entre données et présentation

C'est **le prérequis au travail parallèle** (à faire en commun, en premier).
Aujourd'hui `scrutin/views.py` mélange requêtes ORM et construction Plotly :
c'est exactement la zone que les deux personnes voudraient éditer en même temps.

On la coupe en deux, avec au milieu un dictionnaire simple, sérialisable en JSON :

```
scrutin/donnees.py     [M]  construire_vue_accueil(date) -> dict   (aucun Plotly)
scrutin/graphiques.py  [I]  histogramme(vue) -> div HTML           (aucun ORM)
carte/donnees.py       [M]  resultats_par_commune(sujet) -> dict
carte/figure.py        [I]  carte(donnees) -> div HTML
scrutin/views.py    [commun] assemble les deux, ~15 lignes, rarement touché
```

Forme du contrat (celle que `scrutin/donnees.py` renvoie aujourd'hui) :

```python
{
  "date": "2026-09-27",
  "avance": 0.42,
  "sujets": [
    {"id": 6, "nom": "AVS 21", "oui_connu": 0.512, "oui_extrapole": 0.507,
     "communes": {1: {"oui": 0.61, "comptabilise": True},    # clé = numéro OFS
                  2: {"oui": 0.48, "comptabilise": False}}},  # False = estimé
  ],
}
```

`ic_bas` / `ic_haut` (intervalle de confiance) s'ajouteront avec le bootstrap
de la phase D1 — le test du contrat sera mis à jour à ce moment-là.

Ce n'est **pas un fichier chargé à l'exécution** — juste la forme du dict que
`donnees.py` renvoie et que `graphiques.py` consomme. Elle est figée par
`tests/test_contrat.py`, qui tourne sur la base fictive : si la voie M change la
forme sans prévenir, la CI casse. C'est le garde-fou anti-dérive entre les deux
voies, et le seul endroit qu'on édite à deux.

### Deux jeux de données, un seul chemin de code

Pas de mode maquette, pas de branche `if` dans les vues : **le site tourne
toujours de la même façon**, seule la base change.

| Jeu | Comment | Pour qui |
|---|---|---|
| **Fictif** | `manage.py peupler_demo` | Tout le monde, au quotidien. Une commande depuis un clone frais → site complet et réaliste. |
| **Réel** | pipeline d'import (historique + JSON du jour J) | Voie M : vraies projections, dry run, production. |

Les données fictives doivent être **à l'échelle réelle** — ~2 130 communes, une
dizaine de votations d'historique, plusieurs objets le jour J. Une maquette à
20 communes ne dit rien sur la lisibilité d'une carte ni sur la mise en page.

**Tout est déjà dans le dépôt pour les fabriquer** : `data/K4voge_*.geojson`
contient le nom et le numéro OFS de toutes les communes suisses. `peupler_demo`
n'a donc besoin d'aucun téléchargement — il tourne hors-ligne.

Pour que la démo exerce vraiment le pipeline (et pas juste l'affichage), les
votes fictifs sont tirés à partir d'un profil latent par commune (un axe
urbain/rural, un axe linguistique) plus du bruit : l'ACP y retrouve alors une
vraie structure, et l'extrapolation a quelque chose à apprendre. Graine fixe →
tout le monde voit exactement le même site.

- [x] **[M]** `manage.py peupler_demo` : communes depuis le GeoJSON, historique
      et scrutin en cours fictifs, graine fixe, idempotent.
- [x] **[2]** Écrire `tests/test_contrat.py` : forme du dict figée, exécuté
      sur la base fictive. Proposé côté M (`scrutin/donnees.py` +
      `tests/test_contrat.py`) et validé en PR à deux. `views.py` et la carte
      consomment le contrat (`resultats_par_commune` vit dans
      `scrutin/donnees.py`, pas besoin d'un `carte/donnees.py` à part). Le
      Plotly de l'histogramme attend encore son déménagement de `views.py`
      vers `graphiques.py` **[I]**, celui de la carte de `carte/API.py` vers
      `carte/figure.py` **[I]**.

**Conséquence sur le parallélisme** : la voie I ne démarre qu'une fois le
jalon 0 franchi (A1–A3 + `peupler_demo`, ≈ 1 jour côté M) au lieu de démarrer
immédiatement. C'est le prix de la simplicité — il est faible, et il évite un
mode maquette qui dériverait du vrai site.

### Pourquoi SQLite suffit

- **Un seul écrivain** : le pipeline du jour J tourne dans un seul processus,
  toutes les 2–5 minutes. Aucune écriture concurrente.
- **Volume trivial** : ~2 130 communes × ~55 votations ≈ 120 000 lignes.
- **Lectures servies par le cache/mirroir statique**, pas par la base.
- **Sauvegarde = copier un fichier** (plus simple qu'un `pg_dump`), et le même
  fichier se rejoue à l'identique en local pour déboguer une soirée.
- Activer le mode **WAL** et un `timeout` raisonnable, et c'est réglé.

Cela supprime d'un coup : le service `db` du Compose, `psycopg`,
`dj-database-url`, les variables `db_user`/`db_password`, et la procédure de
sauvegarde Postgres.

### Dépendances séparées

Le site web n'a pas besoin de la pile scientifique : `scipy` et `scikit-learn`
ne servent qu'au calcul (`extrapolation.py`, `populate_pca.py`). Séparer permet
à la voie I d'installer trois paquets au lieu de dix.

- [ ] **[M]** `requirements/web.txt` (django, plotly, geojson) et
      `requirements/calcul.txt` (numpy, scipy, scikit-learn, pandas).
- [ ] **[I]** Bonus : `views.py` n'utilise pandas que pour construire un
      DataFrame passé à `px.bar` — on peut passer des listes directement et
      sortir pandas du chemin web.

### Deux agents Claude, un par voie

Les deux voies sont aussi des **agents** définis dans `.claude/agents/` :
`moteur.md` et `interface.md`. Chacun liste ses fichiers, ses responsabilités et
ses frontières — un agent refuse d'éditer la zone de l'autre.

- **Un clone (ou un worktree git) par agent** : deux agents dans le même
  répertoire se disputeraient l'index git.
- L'agent `interface` travaille sur la base fictive (`peupler_demo`) : ni pile
  scientifique, ni données réelles, ni accès réseau.
- Le **contrat de vue** est leur seul point de rendez-vous : un agent qui a
  besoin d'un champ absent le *demande* au lieu de contourner.
- Les étiquettes **[M]** / **[I]** / **[2]** de ce plan disent à chaque agent ce
  qu'il peut prendre seul et ce qui se décide à deux.

Découpage identique pour deux personnes ou deux agents — c'est le même contrat
qui protège dans les deux cas.

### Rythme et intégration

- Chacun son clone, chacun sa branche, **petites PR relues par l'autre** (c'est
  le principal moment de transfert de connaissance entre les deux voies).
- Rebaser souvent sur `master` : les deux voies touchent peu les mêmes fichiers,
  mais `views.py` et `tests/test_contrat.py` sont partagés.
- Les anciennes branches nominatives `Frederic` / `Laurence` sont abandonnées au
  profit des préfixes `moteur/` et `interface/` — le sujet compte plus que l'auteur.

### Les trois premières séances

1. **Ensemble** : figer la forme du contrat de vue et la couture
   `donnees.py` / `graphiques.py`.
2. **Voie M seule** : A1–A3 + `peupler_demo` — au bout, `manage.py peupler_demo`
   puis `runserver` donnent un site complet depuis un clone frais. C'est le
   jalon qui débloque la voie I.
3. **En parallèle** : voie M sur A4–A5 (bugs, tests), voie I sur la charte CSS
   puis `charte.py`, histogramme, carte.

---

## Partie 1 — État des lieux (résumé)

Le détail est dans [`CLAUDE.md`](CLAUDE.md). L'essentiel pour le plan :

**Ce qui est solide et à préserver**
- La méthode (ACP 6 composantes + régression pondérée le jour J) : validée en
  conditions réelles, c'est le capital du projet.
- Le modèle de données `ResultatCommunalHistorique` (historique) / `ResultatCommunalEnCours` (jour J) /
  `Extrapolation` (instantanés horodatés).
- L'import incrémental des JSON fédéraux (seulement les communes nouvelles).
- Le principe « site statique en production » : insensible à la charge.

**Ce qui bloque une reprise aujourd'hui**
1. Pas de migrations versionnées pour `scrutin` / `pca` — un clone ne démarre pas.
2. `settings.py` exige `/etc/secret_key.txt` et un `../.env` hors repo.
3. Aucune liste de dépendances (`requirements.txt` absent), Python/Django datés (3.1, EOL).
4. Données sources hors repo (`../data/…`) et non documentées.
5. Tout est câblé sur la votation de septembre 2022 (sujets 6/7/8, le « 55 », `range(2)`).
6. Quatre bugs latents identifiés (cache pickle en append, tri sans effet,
   `except` sans `continue`, `Warning()` au lieu de `warnings.warn`).
7. Déploiement par `wget --recursive` dans une boucle `while true`, IP et chemins en dur.

**Phasage retenu**
- **Phase A — Assainir** : repo reproductible, bugs corrigés, tests, CI.
- **Phase B — Moderniser** : Django 5.2, dé-harcoder 2022, pipeline propre.
- **Phase C — Déployer** : Docker Compose sur VPS, génération statique fiabilisée.
- **Phase D — Produit** : cartes réel/estimé, incertitudes, puis élections.

---

## Partie 2 — Phase A : Assainir (priorité n°1)

Objectif de sortie de phase : **un clone frais + `docker compose up` (ou 5 commandes
documentées) donne un site qui tourne en local avec des données de test.** Rien de
nouveau fonctionnellement.

*Phase très majoritairement **[M]**. Elle contient le chemin critique :
`peupler_demo` (A1–A3 + la commande) débloque la voie I, qui enchaîne ensuite la
Partie 7 en parallèle de A4–A5.*

### A1. Reproductibilité du repo **[M]** — *fait*
- [x] `requirements/` avec versions épinglées : `web.txt` (django, plotly,
      geojson) et `calcul.txt` (numpy, scipy, scikit-learn, pandas).
      Plus de `psycopg` — SQLite est dans la bibliothèque standard.
- [x] `.gitignore` : `*.pyc`, `__pycache__/`, `static/`, `cache.pickle`, `.env`,
      `*.sqlite3`, `politiques/` (sortie wget), `votation_matrix.csv`.
- [x] Supprimer `data/switzerland2.geojson` (6 Mo, référencé nulle part) —
      seul `K4voge_20220501_gf.geojson` reste dans `data/`.
- [x] README développeur : mise en route pas à pas, ordre du pipeline de données.

*(Fait au jalon 1, PR #10 « moteur: fondations » — la checklist n'avait pas été
mise à jour à l'époque ; corrigé le 2026-08-30 en relisant le repo.)*

### A2. Configuration saine (`settings.py`) **[M]** — *fait*
- [x] `SECRET_KEY` depuis variable d'environnement, avec valeur de dev par défaut
      si `DEBUG=True` (fini `/etc/secret_key.txt`).
- [x] `DEBUG` : `False` par défaut, activable par env via `env_bool` ; plus de
      parsing fragile `"True"/"False"`.
- [x] `.env.example` versionné, chargé depuis la racine du repo (pas `../.env`).
- [x] **SQLite partout**, chemin paramétrable par env (`DB_PATH`), mode **WAL**
      activé (`PRAGMA journal_mode=WAL`). Plus de `db_user` / `db_password` ni
      d'`ENGINE` postgresql.
- [x] `ALLOWED_HOSTS` depuis env (pas `["*"]` en prod).

*(Fait au jalon 1, PR #10. Idem A1 : checklist mise à jour après coup.)*

### A3. Migrations versionnées **[M]** — *fait*
- [x] `makemigrations scrutin pca carte page_statique` et fichiers committés
      (`scrutin/migrations/0001_initial.py`, `pca/migrations/0001_initial.py`,
      `page_statique/migrations/0001_initial.py`, `carte/migrations/`).

### A4. Corriger les bugs latents (liste fermée, issue de la lecture du code) **[M]** — *fait*
- [x] `scrutin/views.py` : cache pickle ouvert en `'ab'` → **supprimé** (la prod
      est statique, le cache était inutile).
- [x] `Commune.get_last_nb_electeur_slow` : `list(voix).sort()` sans effet →
      `order_by('-sujet_vote__date').first()`.
- [x] `add_initial_scrutin_en_cours` / `update_scrutin_en_cours` : ajouter `continue`
      dans le `except` autour de `get_unique_commune_by_ofs` (sinon la commune de
      l'itération précédente est réutilisée silencieusement).
      **`create_fake_json_input` portait le même bug** — corrigé aussi.
- [x] `ScrutinAPI.getVotationMatrixWithMetaInfo` : `Warning(...)` → `warnings.warn(...)` ;
      ne pas dépendre de la fuite de variable `voixs` après la boucle.
- [x] Remplacer les `except:` nus par des exceptions ciblées.
- [x] `populate_voix.add_foreigner` : `elif len(districts) == 1` teste la mauvaise
      variable (devrait être `len(communes)`) — copier-coller.
- [x] *Bonus, trouvé par le lint* : le message d'erreur des sujets en double dans
      `populate_voix` référençait une variable inexistante (`commune.Canton`) —
      il aurait planté sur un `NameError` au lieu de dire ce qui n'allait pas.

### A5. Tests + CI **[M]** — *fait*
- [x] `pytest` + `pytest-django`. Configuration dans `pyproject.toml`,
      `election/settings_test.py` pour tourner sans `.env`.
- [x] Tests unitaires de `scrutin/extrapolation.py` sur données synthétiques
      (le cœur mathématique — le plus rentable à tester, aucun accès réseau).
- [x] Test d'intégration du pipeline sur la base fictive : `peupler_demo`
      → ACP → extrapolation → une `Extrapolation` cohérente.
- [x] `create_fake_json_input` devient l'outil officiel de répétition générale
      (documenté dans le README).
- [x] GitHub Actions : `ruff` + tests sur chaque PR.
- [ ] **`ruff format` reste à faire, dans une PR à part** : reformater tout le
      dépôt d'un coup produirait un diff illisible mêlé aux corrections, et
      écraserait `git blame`. À décider **[2]**, puisque cela touche les deux
      zones.

### A6. Données — **[I]** sourcing, **[M]** intégration
- [ ] Rapatrier dans le repo (ou dans un `download_data` documenté) les petits
      fichiers sources : liste des communes, méta-info (langue, urbanisation).
- [ ] Documenter la provenance de `donnee_federale_v3.txt` (55 votations
      historiques) et le format attendu — c'est l'intrant de l'ACP, il est
      aujourd'hui irremplaçable s'il est perdu. **À vérifier : en existe-t-il
      encore une copie quelque part ?** Sinon, prévoir un script de
      reconstruction depuis opendata.swiss (B4).

---

## Partie 3 — Phase B : Moderniser

Objectif de sortie de phase : **le site peut couvrir n'importe quelle votation
future sans toucher au code** — seulement la config et les données.

### B1. Mise à jour de la stack **[M]**
- [x] Python 3.12+, Django **5.2 LTS** — épinglé dans `requirements/web.txt`
      depuis le jalon 1 (PR #10). Points d'attention encore ouverts :
      - [x] pandas : `fillna(method='ffill')` déprécié → `.ffill()` (populate_voix) ;
      - [ ] plotly : `px.choropleth_mapbox` déprécié dans les versions récentes →
        `px.choropleth_map` (MapLibre) ; vérifier le rendu des cartes ;
      - [x] la route attrape-tout `path("<str>", …)` → `path("<slug:url>", …)`
        + `get_object_or_404` : une URL inconnue (favicon, page absente de la
        base) renvoie 404 au lieu d'un 500. *Reste côté I* : un `404.html`
        dans la charte. Les liens morts du menu sont traités en D1.
- [x] Passer les scripts `runscript` en **management commands Django natives**
      (`python manage.py <nom> [args]`, `--help`). `scripts/` a disparu, les
      commandes vivent dans `scrutin/management/commands/` (et `populate_pca`
      dans `pca/`) ; django-extensions n'est plus une dépendance. Les noms
      sont conservés. Les chemins `../data/…` des imports historiques sont
      des arguments optionnels avec l'ancien chemin en défaut (A6 décidera
      où vivent ces fichiers). *Trouvé en passant* : `download_data.sh`
      passait les deux JSON à `update_scrutin_en_cours` dans l'ordre inverse
      de celui attendu (courant, précédent) — corrigé.

### B2. Dé-harcoder « septembre 2022 » **[M]** — *fait*
- [x] Sujets affichés (cartes 6/7/8 en dur dans `scrutin/views.py`, 6 dans
      `carte/views.py`) → dériver dynamiquement : « les sujets de la dernière date
      de votation », déjà la logique de `home_view` pour l'histogramme.
      *(Déjà fait au jalon 1, avec `peupler_demo`.)*
- [x] Le « 55 » de `ScrutinAPI` → `nb_sujets_historiques()`, déduit des `ResultatCommunalHistorique`.
      Pas de champ booléen ni de convention par date : un objet est historique
      s'il a des `ResultatCommunalHistorique`, ce qui est déjà la distinction structurante du modèle.
      Le critère « ≥ N % des sujets » est laissé à la Partie 6 — il change les
      entrées de l'ACP, ce n'est pas du dé-harcodage.
- [x] `update_scrutin_en_cours.get_new_commune` : `range(2)` → itère sur tous les
      objets du scrutin (il plantait aussi sur un scrutin à objet unique).
- [x] Noms de fichiers `votation_septembre_2022_*` → arguments de ligne de commande ;
      `download_data.sh` dérive tout de `DATE_SCRUTIN`.
- [x] URL du JSON fédéral paramétrée (elle change à chaque scrutin :
      `sd-t-17-02-<date>-eidgAbstimmung.json`) — construite depuis `DATE_SCRUTIN`.

### B3. Qualité du pipeline **[M]**
- [x] `ScrutinAPI.getVotationMatrixWithMetaInfo` et `get_nb_inscrit` : boucle
      1 requête/commune → une seule requête `select_related` + regroupement en
      mémoire (même optimisation déjà faite pour les cartes, commit d8d43b8).
      Sur la base de démo (2 141 communes × 55 objets) : 4 339 → 3 requêtes pour
      la matrice ACP (1,9 s → 1,1 s), et 20,3 s → 1,3 s pour `get_nb_inscrit`,
      qui interrogeait la base à *chaque* accès à `sujet_vote.date`.
      *Suite* : `get_nb_inscrit` n'avait aucun appelant hors de son propre
      test de non-régression ; supprimée, avec ce test. Un `git revert` la
      ramène si elle servait à quelque chose hors du dépôt.
- [x] Rendre les imports **idempotents** (relançables sans doublons) :
      `update_or_create` plutôt que `save()` aveugle. C'était pire que prévu —
      le doublon n'attendait pas un rejeu : `add_initial_scrutin_en_cours` crée
      la ligne vide, `update_scrutin_en_cours` en créait une **seconde** dès le
      premier import, et l'extrapolation comptait la commune deux fois (une
      réelle, une estimée).
      *Fait* : contrainte d'unicité `(commune, sujet_vote)` en base
      (migration `scrutin/0002`). Elle ne peut pas échouer sur une base
      portant déjà des doublons : la migration les résorbe d'abord, en gardant
      la ligne dépouillée plutôt que la ligne vide.
- [x] Séparer « résultat extrapolé » et « résultat observé » : déjà porté par
      `ResultatCommunalEnCours.comptabilise`, auquel `run_extrapolation` ne touche
      pas. Ni champ dédié ni migration.
- [x] `ScrutinAPI.get_percentage_oui_all_commune` laisse tomber `comptabilise` :
      remonté jusqu'au contrat de vue (`sujet["communes"][ofs]["comptabilise"]`,
      jalon 0), pour les cartes réel/estimé de la phase D.
- [x] Journalisation (`logging`) au lieu de `print` : cinq `print` dans les
      scripts d'import → `logger.warning` / `logger.info`, et un `LOGGING`
      minimal dans `settings.py` (console, niveau INFO) pour que les messages
      d'avancement du jour J restent visibles.

### B4. Données historiques pérennes — **[I]** sources, **[M]** code
- [ ] Script de (re)construction de la matrice historique depuis les données
      ouvertes de la Confédération (opendata.swiss / BFS), pour ne plus dépendre
      du fichier `donnee_federale_v3.txt` au format exotique.
- [ ] Mettre à jour l'historique après chaque votation (les résultats définitifs
      du jour J rejoignent `ResultatCommunalHistorique` → l'ACP se bonifie toute seule). En faire une
      management command : `manage.py archiver_scrutin`.

### B5. Communes dans le temps — fusions et mutations (voir Partie 6) **[2]**
Chantier structurant de la phase B : remplacer les cinq rustines actuelles
(dict `fusions`, exclusions nominatives, OFS « étranger » inventés, filtre
« 55 exact », triple système de clés) par un **référentiel de communes historisé**
importé depuis l'OFS. Détail complet en Partie 6. C'est le prérequis réel de
l'objectif de phase — le site dort depuis 2022, la reprise absorbera ~4 ans de
mutations d'un coup.

---

## Partie 4 — Phase C : Déployer proprement (VPS Infomaniak)

Objectif de sortie de phase : **un dimanche de votation se lance avec une seule
commande, et le site survit à un pic de trafic.**

### C1. Conteneurisation **[M]**
- [ ] Docker Compose à **deux services** : `web` (gunicorn) et `proxy`
      (Caddy ou nginx, HTTPS automatique). Pas de service `db` — le fichier
      SQLite vit dans un volume monté. Réutiliser les patterns éprouvés de
      `quantinemo-frontend/infra` (même hébergeur, même gabarit de VPS).
- [ ] Secrets par `.env` non versionné + `.env.example` ; sauvegarde =
      **copie datée du fichier SQLite** (`VACUUM INTO`, sûr à chaud),
      quotidienne — l'historique `ResultatCommunalHistorique` est le bien précieux du projet.

### C2. Remplacer la boucle `wget --recursive` **[M]**
Le principe statique est bon ; l'implémentation est fragile. Deux options :

- **Option 1 (recommandée) — micro-cache nginx devant Django** : `proxy_cache`
  30–60 s sur toutes les pages. Django tourne en continu, le VPS 1 vCPU tient
  n'importe quel pic (quelques requêtes/minute atteignent réellement Django).
  Plus simple : plus de mirroir, plus de copie, le site est toujours à jour.
- **Option 2 — export statique propre** : une management command
  `manage.py export_site` qui rend les vues en HTML (`render_to_string`) vers un
  dossier servi par le proxy. Même garantie que l'actuel wget, sans wget.

Dans les deux cas :
- [ ] La boucle du jour J devient un **timer systemd** (ou boucle supervisée) :
      `fetch JSON → update → extrapolation → (export)`, toutes les 2–5 min,
      avec logs et reprise sur erreur — plus de `while true` dans un terminal SSH.
- [ ] Chemins, URL du scrutin et cadence en config, plus rien en dur.

### C3. Répétition générale **[2]**
- [ ] Procédure écrite de « dry run » avec `create_fake_json_input` : simuler une
      soirée complète sur le VPS **avant** chaque vraie votation.
- [ ] Checklist jour J (mettre à jour l'URL du JSON, vérifier l'ACP, lancer le
      timer, contrôle visuel) versionnée dans le repo.

---

## Partie 5 — Phase D : Produit (après A–C)

### D1. Votations — améliorations visibles — **[I]** rendu, **[M]** stats
- [ ] Cartes distinguant **réel vs estimé** (les données le permettront après B3) :
      opacité/hachures ou bascule, légende explicite.
- [ ] **Incertitude de la projection** : IC par bootstrap sur les communes
      dépouillées (rééchantillonner, réajuster, propager). Afficher une fourchette
      plutôt qu'un point — c'est LA crédibilité scientifique du site.
- [ ] Courbe de **convergence de la soirée** : les instantanés `Extrapolation`
      horodatés sont déjà en base, il n'y a qu'à les tracer (projection vs heure,
      avec le résultat final en ligne de référence).
- [x] **Décidé le 2026-09-01 : `page_statique` reste en base**, contre l'idée
      initiale de ce plan (fichiers markdown versionnés). L'app date de 2022,
      fait vingt lignes, ne coûte rien à maintenir, et corriger une coquille un
      soir de votation ne demande ni commit ni redémarrage : le miroir statique
      reprend la correction au tour de boucle suivant. Le prix accepté : ce
      contenu échappe à git, donc ni revue, ni historique, ni retour arrière.
      Ce qui était réellement bancal, ce n'est pas le stockage mais la
      **coupure menu / contenu** : les onglets sont en dur dans `base.html`,
      donc ajouter une page oblige de toute façon à éditer le gabarit, et une
      page écrite dans un clone n'existe pas dans l'autre. D'où les trois
      tâches ci-dessous, qui remplacent la migration vers markdown.
- [x] **[M]** Menu construit depuis la base : le *context processor*
      `page_statique.context_processors.menu` injecte `pages_statiques` dans
      tous les gabarits, triées par le nouveau champ `ordre` puis par titre
      (migration `0002`).
- [x] **[I]** `base.html` boucle sur `pages_statiques` au lieu des `<a>` en
      dur. Fait côté M **à la demande de Frédéric**, malgré la règle des zones.
      Accueil et Cartes restent écrits à la main, ce sont de vraies routes ;
      les trois liens passent par `{% url %}`, ce qui a réparé l'onglet Cartes
      qui pointait sur `NA`.
      Accueil et Cartes restent écrits à la main : ce sont de vraies routes,
      pas des pages en base. Au passage, l'onglet Cartes pointe sur `NA`, qui
      n'existe pas : la route est `/cartes`.
- [x] **[M]** `peupler_demo` sème « Méthodes » et « Contact », contenu
      squelettique, et `_vider()` purge désormais `PageStatique` : un clone
      frais a un menu qui marche.
- [ ] **[2]** Page « Méthodes » réécrite — le contenu lui-même, pas le support.
- [ ] Validation rétrospective : rejouer les votations passées et publier l'erreur
      de projection en fonction de l'avance du dépouillement.

### D2. Élections (intégration d'`extrapolation_politique`) **[2]**
Généraliser du binaire oui/non au multi-candidats :
- [ ] Modèles : `Scrutin` (votation OU élection), `Candidat`,
      `ResultatCandidat(commune, candidat, voix)` — `ResultatCommunalHistorique` actuel devient le cas
      particulier à deux « candidats ».
- [ ] Porter la méthode du repo `extrapolation_politique` (reports de voix
      1er → 2e tour par moindres carrés) comme **second modèle d'extrapolation**,
      à côté du modèle ACP. En corriger les limites connues : contraindre les
      coefficients (≥ 0, sommes ≤ 1 — `scipy.optimize` avec bornes/contraintes),
      pondération par taille de commune.
- [ ] Sources de données cantonales (VD d'abord — formats déjà connus du repo
      élection vaudoise 2022).
- [ ] UI : barres empilées confirmé/extrapolé par candidat (le graphique de
      `projection` dans extrapolation_politique, en propre).

---

## Roadmap récapitulative

| Jalon | Voie M — Moteur | Voie I — Interface |
|---|---|---|
| **0. Contrat** *(à deux, en premier)* | forme du dict + couture `donnees`/`graphiques` | idem |
| **1. Le repo démarre** | A1–A3 + `peupler_demo` — **débloque la voie I** | (attend le jalon 1) |
| **2. Base saine** | A4–A5 : bugs, tests, CI | P7 : charte CSS, `charte.py`, histogramme, carte |
| **3. Prêt pour un scrutin** | B1–B4 : Django 5.2, dé-harcodage, pipeline | P7 : chiffre héro, a11y, hygiène |
| **4. Communes historisées** | Partie 6 : modèle + résolution | Partie 6 : sources OFS, contrôle qualité |
| **5. En production** | C1–C2 : Compose, cache, timer systemd | C3 : contrôle visuel du dry run |
| **6. Produit** | D1 : IC bootstrap, données de convergence | D1 : réel/estimé, courbe, page Méthodes |
| **7. Élections** | D2 : modèles généralisés, méthode reports | D2 : UI multi-candidats |

Effort indicatif côté M : A ≈ 2–4 j, B ≈ 3–5 j, C ≈ 2–3 j. Côté I, la Partie 7
est largement parallélisable et peut démarrer dès le jalon 0.

**Chemin critique : le jalon 1.** Tant que `peupler_demo` n'existe pas, la voie I
n'a pas de site à regarder. C'est ≈ 1 jour de travail côté M — à faire en premier,
avant tout le reste.

**Cible naturelle** : être prêt (fin de C, dry run inclus) pour la **prochaine
votation fédérale** — vérifier la date sur admin.ch et compter ~2 semaines de marge
pour la répétition générale.

**Ordre des premières actions concrètes**

*À deux, d'abord* — figer la forme du contrat de vue et la couture
`donnees.py` / `graphiques.py`.

*Puis voie M* (c'est le chemin critique) :
1. `requirements/` + `.gitignore` + venv qui s'installe.
2. `settings.py` assaini (env vars, SQLite + WAL) — le repo démarre enfin.
3. `makemigrations` + commit des migrations.
4. **`manage.py peupler_demo`** — à partir de là, la voie I est débloquée.
5. Corrections des bugs latents (petites PR séparées).
6. Tests de `extrapolation.py` + CI.

*Puis voie I* :
1. Charte en variables CSS + fonte unique + contrastes corrigés.
2. `charte.py` (template Plotly partagé), puis histogramme (ligne des 50 %),
   puis carte (divergente ancrée à 50 %).
3. Chiffre héro, tableaux de valeurs, hygiène (SVG, favicon, Plotly vendoré).

---

## Partie 6 — Gestion des mutations de communes (design)

### Le problème
La Suisse fusionne 10 à 30 communes par an (plus renommages, changements de
canton, échanges de territoire). Le code actuel gère ça par cinq mécanismes
ad hoc, tous fragiles :

1. **Dict `fusions` en dur** (`populate_voix.py:5`) : 19 communes → héritière,
   appariées **par nom**, sommées à l'import historique. Contient déjà un cas
   non trivial : Clavaleyres → Murten est un **changement de canton** (BE→FR).
2. **Exclusions nominatives** de Rüti bei Lyssach / Jaberg dans 3 scripts jour-J.
   Cause racine : commune présente en base mais sans les 55 `ResultatCommunalHistorique` → pas de
   `PCAResult` → `get_extrapolation` lève et **tout le jour J plante**.
3. **Pseudo-communes « XX-étranger »** avec OFS 9010–9250 attribués à la main,
   détectées par sous-chaîne `Ausland/étranger/estero`.
4. **Filtre « exactement 55 ResultatCommunalHistorique »** : écarte silencieusement de l'ACP toute
   commune à historique incomplet (le `Warning()` sans effet masque tout).
5. **Trois systèmes de clés** : historique par nom, jour J par n° OFS, cartes par
   `vogeId`/`vogeName` sur un GeoJSON millésimé 2022-05-01.

Chaque mutation = du code à éditer à plusieurs endroits ; tout oubli = crash le
soir du scrutin ou commune silencieusement perdue.

### Le design cible : référentiel historisé (les mutations = des données)

**Source officielle** : le Répertoire officiel des communes **historisé** de
l'OFS (norme **eCH-0071**, application AGVCH) : identifiant d'historisation
stable par commune, périodes de validité, catalogue complet des mutations.

**Modèle** :
```python
class CommuneVersion:            # une commune PENDANT une période
    hist_id                      # id d'historisation OFS — LA clé interne
    numero_ofs                   # réutilisable dans le temps, jamais clé
    nom, canton, district
    valide_de, valide_a          # valide_a=None ⇒ commune actuelle

class Mutation:
    date_effet, type             # fusion / scission / renommage / chgt canton
    ancetres    = M2M(CommuneVersion)
    successeurs = M2M(CommuneVersion)
```
→ un DAG temporel. Toute la logique spéciale se réduit à une fonction
`resoudre(version, date_cible)` qui suit les arêtes de mutation vers l'avant.

**Conséquences** :
- **Appariement** partout par `(numero_ofs, date du scrutin)` → version ;
  les noms ne servent qu'à l'affichage (fini `"Kirchdorf (BE)"`).
- **Matrice ACP « vue d'aujourd'hui »** : pour chaque commune actuelle, sommer
  les oui/non de ses ancêtres à chaque votation, puis calculer les %. Le dict
  `fusions` disparaît ; le « 55 exact » devient un seuil de couverture (≥ 90 %).
- **Jour J blindé** : commune sans profil ACP → repli sur le profil moyen du
  district + log, plus jamais d'exception qui tue l'extrapolation.
- **Maintenance** : `manage.py maj_communes` rejouée avant chaque scrutin
  importe les nouvelles mutations depuis l'OFS. Zéro code à toucher.
- **Approximations assumées** (documentées) : échanges partiels de territoire
  traités comme « pas de mutation » ; « XX-étranger » gardés comme
  pseudo-entités hors carte mais **dans** l'extrapolation (profil de vote
  distinct = signal utile).
- **GeoJSON** : millésime swisstopo assorti à la date du scrutin, date stockée
  en config.

### Ordre d'implémentation **[2]**
1. Import eCH-0071 → `CommuneVersion` + `Mutation` (management command).
2. Ré-appariement de l'historique `ResultatCommunalHistorique` sur les versions (par OFS + date —
   supprime le matching par nom).
3. Construction de la matrice ACP par résolution (supprime `fusions` et le 55).
4. Jour J : résolution + replis (supprime les exclusions nominatives).
5. Test de non-régression : mêmes projections qu'avant sur les données de
   septembre 2022 rejouées.

---

## Partie 7 — Qualité graphique & CSS (audit + refonte)

Chantier **indépendant des phases A–C** : peut démarrer tôt, aucune dépendance
au backend. Alimente D1.

### État des lieux — HTML/CSS **[I]**
- `lang="en"` sur un site francophone ; `<link>` Font Awesome dans le `<body>`
  (HTML invalide) — et FA 4.7 (2016) chargé pour **une** icône ☰.
- Lien mort `href="NA"` (Cartes) ; pas de favicon ni meta description ;
  footer « 2022 » en dur.
- Couleurs CSS nommées (`CornflowerBlue`, `DimGrey`, `whitesmoke`) ; le bleu
  CornflowerBlue sur fond blanc ≈ **2,7:1** — sous le seuil de lisibilité 4,5:1
  pour la navigation et les titres.
- Trois familles typographiques concurrentes : Garamond (titres/nav),
  Courier New (sous-titres), + la fonte par défaut de Plotly dans les graphes.
- Scories : `#main p { color: red }`, sélecteur `.navitation` (typo, règle
  morte), `max-height: 80px` qui tronque le bandeau, commentaires
  d'apprentissage flexbox.
- Aucune variable CSS → pas de charte tenable dans le temps.

### État des lieux — graphiques Plotly **[I]**
- **Couleurs par défaut de plotly.express** (#636efa/#EF553B), jamais choisies.
- Histogramme : **pas de ligne de référence à 50 %** — le seuil de majorité,
  l'information n°1 d'une votation ; un label sur chaque barre (bruit) ;
  modebar Plotly visible ; titre vide.
- Carte : échelle **RdYlGn = rouge/vert, le piège daltonien par excellence**,
  et bornée aux percentiles 10–90 → le point médian de l'échelle ne
  correspond à rien (surtout pas à 50 %) ; `opacity=0.5` délave tout.
- Bon point à préserver : `white-bg` sans tuiles externes → compatible avec le
  mirroir statique, aucune dépendance à un serveur de cartes.

### Refonte proposée **[I]**
1. **Mini-charte en variables CSS** (`--surface`, `--encre-1/2`, `--bleu-450`…,
   valeurs de la palette validée ci-dessous) ; **une seule fonte** : la sans
   système (`system-ui, …`) partout — Garamond peut survivre dans le seul
   wordmark du logo. Nav/titres dans un bleu ≥ 4,5:1 (ex. `#1c5cab`).
2. **Module `charte.py`** : constantes de couleurs + template Plotly partagé
   (fonte, grille hairline `#e1e0d9`, `modebar` masquée, marges, fond
   `#fcfcfb`) appliqué à *tous* les graphes — un seul endroit à modifier.
3. **Histogramme votations** : confirmé = bleu `#2a78d6`, extrapolé = bleu
   clair `#86b6ef` (même teinte, plus clair = estimé — la variante validée
   `--ordinal` ; l'alternative bleu/orange `#2a78d6`/`#eb6834` est aussi
   validée). **Ligne de référence à 50 %** (hairline, étiquetée « majorité »).
   Labels sélectifs : le total projeté seulement, le reste en tooltip.
4. **Carte** : échelle **divergente bleu ↔ rouge, milieu gris neutre
   (`#f0efec`) ancré à 50 %** — « penche oui / penche non » lisible d'un coup
   d'œil, y compris pour les daltoniens. Bornes symétriques autour de 50.
   Garder `white-bg` ; migrer `choropleth_mapbox` → `choropleth_map`.
5. **Chiffre héro** : par objet, le % oui projeté en grand + « accepté/refusé »
   attendu — c'est la une du site, aujourd'hui à déchiffrer dans les barres.
6. **Accessibilité** : tableau des valeurs sous chaque graphe (repli
   sans-couleur + copiable), `lang="fr"`, alt/aria sur la nav.
7. **Hygiène** : icône ☰ en SVG inline (supprimer Font Awesome), favicon,
   liens réparés, **vendorer `plotly.min.js`** (le CDN casse le mirroir wget
   hors-ligne et fige la version), année du footer dynamique.

Palettes validées (`validate_palette.js`, surface `#fcfcfb`) :
- `#2a78d6` + `#eb6834` : tous contrôles PASS (ΔE daltonien 24,7 ; normal 33,6).
- `#86b6ef` → `#2a78d6` en ordinal : PASS (monotone, une teinte, écarts ok).
