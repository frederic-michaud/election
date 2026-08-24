# Plan de modernisation — Politiques.ch

*Établi le 24 août 2026. Document de travail : cocher / annoter au fil de l'eau.*

## Décisions actées

- **Architecture** : on garde Django, modernisé (Django 5.2 LTS, Python 3.12+).
- **Priorité n°1** : assainir la base avant toute nouvelle fonctionnalité.
- **Hébergement** : VPS Infomaniak, comme avant (Docker Compose envisagé).
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
| `maquette/` | **I** |
| `*/views.py` | **commun** — doit rester minuscule (voir couture) |
| `fixtures/*.json` | **commun** — c'est le contrat, on l'édite ensemble |
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

Forme du contrat (à figer ensemble, puis versionnée dans `fixtures/`) :

```json
{
  "date": "2026-09-27",
  "avance": 0.42,
  "sujets": [
    {"id": 6, "nom": "AVS 21", "oui_connu": 0.512, "oui_extrapole": 0.507,
     "ic_bas": 0.494, "ic_haut": 0.520,
     "communes": {"1": 0.61, "2": 0.48}}
  ]
}
```

**Le contrat est un fichier `fixtures/vue_accueil.json` versionné.** Un test de
la voie M vérifie que `construire_vue_accueil()` produit exactement ces clés :
si le backend change de forme sans mettre à jour la fixture, la CI casse. C'est
le garde-fou anti-dérive entre les deux voies.

### Maquetter avant que l'infra soit prête

Quatre niveaux, du plus léger au plus complet. **La voie I vit aux niveaux 0–2 et
n'a jamais besoin de Postgres, ni de scikit-learn, ni des 55 votations
historiques.**

| Niveau | Ce qu'il faut | Pour quoi |
|---|---|---|
| **0 — HTML statique** | un navigateur | Explorer la charte, les couleurs, la mise en page. Un `maquette/index.html` autonome avec des `<div>` Plotly figés. Itération en secondes, partageable par simple fichier. |
| **1 — Django + fixture** | `django`, `plotly` | Vrais templates, vraies figures générées en Python, **zéro base de données** : `MODE_FIXTURE=1 python manage.py runserver` lit `fixtures/vue_accueil.json` au lieu de l'ORM. Mode de travail principal de la voie I. |
| **2 — SQLite + données de démo** | + `manage.py loaddata demo` | Chemin ORM réel sur ~20 communes et 3 sujets. Sert à vérifier que le vrai `donnees.py` remplit bien le contrat. |
| **3 — Pile complète** | Postgres, pipeline, scipy/sklearn | Monde de la voie M : vraies extrapolations, dry run du jour J. |

Mise en œuvre du niveau 1 (petite, à faire tôt) :
```python
# scrutin/views.py
def home_view(requete):
    if settings.MODE_FIXTURE:
        vue = json.loads(Path("fixtures/vue_accueil.json").read_text())
    else:
        vue = donnees.construire_vue_accueil()
    return render(requete, "home.html", graphiques.tout(vue))
```

- [ ] **[2]** Figer la forme du contrat et écrire `fixtures/vue_accueil.json`
      (à la main, ou généré depuis les données de septembre 2022 si on les
      retrouve — une vraie soirée fait une bien meilleure maquette).
- [ ] **[2]** Ajouter `MODE_FIXTURE` dans les settings + la bascule dans les vues.
- [ ] **[M]** Test de conformité `donnees.py` ↔ fixture.
- [ ] **[I]** `maquette/index.html` de niveau 0 pour l'exploration graphique.

### Dépendances séparées

Le site web n'a pas besoin de la pile scientifique : `scipy` et `scikit-learn`
ne servent qu'au calcul (`extrapolation.py`, `populate_pca.py`). Séparer permet
à la voie I d'installer trois paquets au lieu de dix.

- [ ] **[M]** `requirements/web.txt` (django, plotly, geojson, psycopg) et
      `requirements/calcul.txt` (numpy, scipy, scikit-learn, pandas).
- [ ] **[I]** Bonus : `views.py` n'utilise pandas que pour construire un
      DataFrame passé à `px.bar` — on peut passer des listes directement et
      sortir pandas du chemin web.

### Rythme et intégration

- Chacun son clone, chacun sa branche, **petites PR relues par l'autre** (c'est
  le principal moment de transfert de connaissance entre les deux voies).
- Rebaser souvent sur `master` : les deux voies touchent peu les mêmes fichiers,
  mais `views.py` et les fixtures sont partagés.
- Les anciennes branches nominatives `Frederic` / `Laurence` sont abandonnées au
  profit des préfixes `moteur/` et `interface/` — le sujet compte plus que l'auteur.

### Les trois premières séances

1. **Ensemble** : figer le contrat + écrire la fixture + poser `MODE_FIXTURE`.
   Après ça, les deux voies sont découplées.
2. **Voie M** : A1–A3 (le repo démarre). **Voie I** : maquette niveau 0, charte CSS.
3. **Voie M** : A4–A5 (bugs, tests). **Voie I** : `charte.py`, histogramme, carte.

---

## Partie 1 — État des lieux (résumé)

Le détail est dans [`CLAUDE.md`](CLAUDE.md). L'essentiel pour le plan :

**Ce qui est solide et à préserver**
- La méthode (ACP 6 composantes + régression pondérée le jour J) : validée en
  conditions réelles, c'est le capital du projet.
- Le modèle de données `Voix` (historique) / `ScrutinEnCours` (jour J) /
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

*Phase très majoritairement **[M]**. Pendant ce temps la voie I travaille la
Partie 7 en mode fixture — c'est tout l'intérêt de la couture du jalon 0.*

### A1. Reproductibilité du repo **[M]**
- [ ] `requirements.txt` (ou `pyproject.toml`) avec versions épinglées :
      `django`, `django-extensions`, `python-dotenv`, `psycopg[binary]`, `pandas`,
      `numpy`, `scipy`, `scikit-learn`, `plotly`, `geojson`.
- [ ] `.gitignore` : `*.pyc`, `__pycache__/`, `static/`, `cache.pickle`, `.env`,
      `db.sqlite3`, `politiques/` (sortie wget), `votation_matrix.csv`.
- [ ] Supprimer `data/switzerland2.geojson` (6 Mo, référencé nulle part).
- [ ] README développeur : mise en route pas à pas, ordre du pipeline de données.

### A2. Configuration saine (`settings.py`) **[M]**
- [ ] `SECRET_KEY` depuis variable d'environnement, avec valeur de dev par défaut
      si `DEBUG=True` (fini `/etc/secret_key.txt`).
- [ ] `DEBUG` : `False` par défaut, activable par env ; supprimer le parsing fragile
      `"True"/"False"` (utiliser `os.environ.get("DEBUG") == "1"` ou équivalent).
- [ ] `.env.example` versionné, chargé depuis la racine du repo (pas `../.env`).
- [ ] Base de données par `DATABASE_URL` (dj-database-url) : Postgres en prod,
      **SQLite par défaut en dev** — supprime la dépendance Postgres pour bosser.
- [ ] `ALLOWED_HOSTS` depuis env (pas `["*"]` en prod).

### A3. Migrations versionnées **[M]**
- [ ] `makemigrations scrutin pca carte` et committer les fichiers.
- [ ] Vérifier que le schéma généré correspond à la base de prod historique
      (si un dump existe encore) ; sinon assumer le schéma neuf comme référence.

### A4. Corriger les bugs latents (liste fermée, issue de la lecture du code) **[M]**
- [ ] `scrutin/views.py` : cache pickle ouvert en `'ab'` → soit le supprimer
      (recommandé : la prod est statique, le cache est inutile), soit `'wb'` + vraie
      invalidation.
- [ ] `Commune.get_last_nb_electeur_slow` : `list(voix).sort()` sans effet →
      `order_by('-sujet_vote__date').first()`.
- [ ] `add_initial_scrutin_en_cours` / `update_scrutin_en_cours` : ajouter `continue`
      dans le `except` autour de `get_unique_commune_by_ofs` (sinon la commune de
      l'itération précédente est réutilisée silencieusement).
- [ ] `ScrutinAPI.getVotationMatrixWithMetaInfo` : `Warning(...)` → `warnings.warn(...)` ;
      ne pas dépendre de la fuite de variable `voixs` après la boucle.
- [ ] Remplacer les `except:` nus par des exceptions ciblées (`Commune.DoesNotExist`
      une fois les helpers convertis en `objects.get(...)`).
- [ ] `populate_voix.add_foreigner` : `elif len(districts) == 1` teste la mauvaise
      variable (devrait être `len(communes)`) — copier-coller.

### A5. Tests + CI **[M]**
- [ ] `pytest` + `pytest-django`.
- [ ] Tests unitaires de `scrutin/extrapolation.py` sur données synthétiques
      (le cœur mathématique — le plus rentable à tester, aucun accès réseau).
- [ ] Test d'intégration du pipeline : fixtures minimales (3 communes, 3 sujets)
      → `populate_pca` → `run_extrapolation` → une `Extrapolation` cohérente.
- [ ] `create_fake_json_input` devient l'outil officiel de répétition générale
      (le documenter comme tel).
- [ ] GitHub Actions : `ruff` (lint + format) + tests sur chaque PR.

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
- [ ] Python 3.12+, Django **5.2 LTS**. Le code est simple, la migration 3.1 → 5.2
      devrait être douce. Points d'attention connus :
      - `psycopg2` → `psycopg` v3 (changer `ENGINE` si besoin) ;
      - pandas : `fillna(method='ffill')` déprécié → `.ffill()` (populate_voix) ;
      - plotly : `px.choropleth_mapbox` déprécié dans les versions récentes →
        `px.choropleth_map` (MapLibre) ; vérifier le rendu des cartes ;
      - la route attrape-tout `path("<str>", …)` fonctionne mais mérite
        `path("<slug:url>", …)` + 404 propre au lieu d'une exception brute.
- [ ] Passer les scripts `runscript` en **management commands Django natives**
      (`python manage.py import_votations …`). Supprime la dépendance à
      django-extensions et donne argparse, `--help`, tests faciles.

### B2. Dé-harcoder « septembre 2022 » **[M]**
- [ ] Sujets affichés (cartes 6/7/8 en dur dans `scrutin/views.py`, 6 dans
      `carte/views.py`) → dériver dynamiquement : « les sujets de la dernière date
      de votation », déjà la logique de `home_view` pour l'histogramme.
- [ ] Le « 55 » de `ScrutinAPI` (nombre de votations historiques) → calculé :
      `SujetVote.objects.filter(historique).count()`, ou critère « la commune a un
      résultat pour ≥ N % des sujets ». Marquer les sujets historiques vs jour J
      (champ booléen ou convention par date).
- [ ] `update_scrutin_en_cours.get_new_commune` : `range(2)` → itérer sur tous les
      objets du scrutin (il peut y en avoir 1, 3, 4…).
- [ ] Noms de fichiers `votation_septembre_2022_*` → chemin/date paramétrés.
- [ ] URL du JSON fédéral paramétrée (elle change à chaque scrutin :
      `sd-t-17-02-<date>-eidgAbstimmung.json`).

### B3. Qualité du pipeline **[M]**
- [ ] `ScrutinAPI.getVotationMatrixWithMetaInfo` et `get_nb_inscrit` : boucle
      1 requête/commune → une seule requête `select_related` + regroupement en
      mémoire (même optimisation déjà faite pour les cartes, commit d8d43b8).
- [ ] Rendre les imports **idempotents** (relançables sans doublons) :
      `update_or_create` plutôt que `save()` aveugle ; aujourd'hui relancer
      `update_scrutin_en_cours` sur le même JSON crée des doublons de
      `ScrutinEnCours`.
- [ ] Séparer clairement « résultat extrapolé » et « résultat observé » :
      `run_extrapolation` écrit actuellement les estimations **dans**
      `ScrutinEnCours` (champs oui/non des communes non dépouillées). Ajouter des
      champs dédiés (`oui_estime`, …) ou une table `ExtrapolationCommune` — condition
      préalable aux cartes réel/estimé de la phase D.
- [ ] Journalisation (`logging`) au lieu de `print`.

### B4. Données historiques pérennes — **[I]** sources, **[M]** code
- [ ] Script de (re)construction de la matrice historique depuis les données
      ouvertes de la Confédération (opendata.swiss / BFS), pour ne plus dépendre
      du fichier `donnee_federale_v3.txt` au format exotique.
- [ ] Mettre à jour l'historique après chaque votation (les résultats définitifs
      du jour J rejoignent `Voix` → l'ACP se bonifie toute seule). En faire une
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
- [ ] Docker Compose : `web` (gunicorn), `db` (Postgres + volume), `proxy`
      (Caddy ou nginx, HTTPS automatique). Réutiliser les patterns éprouvés de
      `quantinemo-frontend/infra` (même hébergeur, même gabarit de VPS).
- [ ] Secrets par `.env` non versionné + `.env.example` ; sauvegardes `pg_dump`
      quotidiennes (l'historique `Voix` est précieux).

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
- [ ] Page « Méthodes » réécrite ; passer `page_statique` (contenu en DB) à des
      fichiers markdown versionnés rendus par Django.
- [ ] Validation rétrospective : rejouer les votations passées et publier l'erreur
      de projection en fonction de l'avance du dépouillement.

### D2. Élections (intégration d'`extrapolation_politique`) **[2]**
Généraliser du binaire oui/non au multi-candidats :
- [ ] Modèles : `Scrutin` (votation OU élection), `Candidat`,
      `ResultatCandidat(commune, candidat, voix)` — `Voix` actuel devient le cas
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
| **0. Découplage** *(à deux, en premier)* | contrat de vue + `MODE_FIXTURE` | contrat de vue + `MODE_FIXTURE` |
| **1. Le repo démarre** | A1–A3 : requirements, settings, migrations | P7 : maquette niveau 0, charte CSS |
| **2. Base saine** | A4–A5 : bugs, tests, CI | P7 : `charte.py`, histogramme, carte |
| **3. Prêt pour un scrutin** | B1–B4 : Django 5.2, dé-harcodage, pipeline | P7 : chiffre héro, a11y, hygiène |
| **4. Communes historisées** | Partie 6 : modèle + résolution | Partie 6 : sources OFS, contrôle qualité |
| **5. En production** | C1–C2 : Compose, cache, timer systemd | C3 : contrôle visuel du dry run |
| **6. Produit** | D1 : IC bootstrap, données de convergence | D1 : réel/estimé, courbe, page Méthodes |
| **7. Élections** | D2 : modèles généralisés, méthode reports | D2 : UI multi-candidats |

Effort indicatif côté M : A ≈ 2–4 j, B ≈ 3–5 j, C ≈ 2–3 j. Côté I, la Partie 7
est largement parallélisable et peut démarrer dès le jalon 0.

**Chemin critique : le jalon 0.** Tant que le contrat n'est pas posé, les deux
voies se disputent `views.py` ; une fois posé, elles ne se croisent presque plus
jusqu'au jalon 5.

**Cible naturelle** : être prêt (fin de C, dry run inclus) pour la **prochaine
votation fédérale** — vérifier la date sur admin.ch et compter ~2 semaines de marge
pour la répétition générale.

**Ordre des premières actions concrètes**

*À deux, d'abord* — figer le contrat de vue, écrire `fixtures/vue_accueil.json`,
poser `MODE_FIXTURE`. Sans ça, pas de parallélisme.

*Puis voie M* :
1. `requirements/` + `.gitignore` + venv qui s'installe.
2. `settings.py` assaini (env vars, SQLite en dev) — le repo démarre enfin.
3. `makemigrations` + commit des migrations.
4. Corrections des bugs latents (petites PR séparées).
5. Tests de `extrapolation.py` + CI.

*Puis voie I* :
1. `maquette/index.html` : explorer palette, typo, mise en page sans Django.
2. Charte en variables CSS + fonte unique + contrastes corrigés.
3. `charte.py` (template Plotly partagé), puis histogramme (ligne des 50 %),
   puis carte (divergente ancrée à 50 %).

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
   Cause racine : commune présente en base mais sans les 55 `Voix` → pas de
   `PCAResult` → `get_extrapolation` lève et **tout le jour J plante**.
3. **Pseudo-communes « XX-étranger »** avec OFS 9010–9250 attribués à la main,
   détectées par sous-chaîne `Ausland/étranger/estero`.
4. **Filtre « exactement 55 Voix »** : écarte silencieusement de l'ACP toute
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
2. Ré-appariement de l'historique `Voix` sur les versions (par OFS + date —
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
