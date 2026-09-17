# Politiques.ch

Projection en direct des résultats des votations fédérales suisses, le dimanche
de scrutin : à partir des communes déjà dépouillées, le site extrapole les
communes manquantes et affiche le pourcentage de oui attendu.

- Méthode, architecture et pièges connus : [`CLAUDE.md`](CLAUDE.md)
- Feuille de route : [`PLAN_MODERNISATION.md`](PLAN_MODERNISATION.md)

## Mise en route

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements/dev.txt

cp .env.example .env          # DEBUG=1 suffit pour travailler en local
python manage.py migrate
python manage.py peupler_demo
python manage.py runserver
```

La base est **SQLite** (`votation.sqlite3` à la racine) — rien à installer.

Par défaut, `runserver` n'écoute que sur `127.0.0.1` : le site n'est visible
que depuis la machine qui l'exécute.

### Accès depuis une autre machine

Utile quand le serveur tourne sur une machine distante (VM sans navigateur,
par exemple) et qu'on veut le consulter depuis son propre poste.

1. **Écouter sur toutes les interfaces**, pas seulement `127.0.0.1` :
   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```
   Choisir un port libre sur la machine (`ss -tlnp` pour vérifier) si `8000`
   est déjà pris par autre chose.
2. **Ajouter l'hôte à `ALLOWED_HOSTS`** dans `.env` — sinon Django rejette la
   requête avec une erreur `DisallowedHost` dès que l'en-tête `Host:` ne
   correspond pas à la liste :
   ```
   ALLOWED_HOSTS=localhost,127.0.0.1,<IP ou nom d'hôte de la machine>
   ```
3. Ouvrir `http://<IP ou nom d'hôte>:<port>/` depuis le navigateur du poste
   distant.

Ce mode reste un serveur de développement (`runserver`), pas un déploiement
de production — voir [`PLAN_MODERNISATION.md`](PLAN_MODERNISATION.md) pour la
cible (Docker Compose + proxy HTTPS).

## Jeux de dépendances

| Fichier | Contenu | Pour |
|---|---|---|
| `requirements/web.txt` | Django, Plotly, geojson | faire tourner le site |
| `requirements/calcul.txt` | + numpy, scipy, scikit-learn, pandas | extrapolation et ACP |
| `requirements/dev.txt` | + pytest, ruff | développer |

Travailler sur l'interface ne demande que `web.txt` : la pile scientifique ne
sert qu'au calcul des projections.

## Données

Deux jeux, **un seul chemin de code** — seule la base change.

**Fictives** (usage quotidien) : `python manage.py peupler_demo`. Construit une
base à l'échelle réelle (~2 130 communes) sans aucun téléchargement, à graine
fixe — tout le monde voit exactement le même site. Les deux pages du menu
(Méthodes, Contact) sont semées elles aussi, sinon leurs onglets tomberaient
en 404.

**Réelles** : voir le pipeline d'import décrit dans [`CLAUDE.md`](CLAUDE.md).

## Tests et qualité

```bash
pytest                 # toute la suite (~10 s)
pytest -m "not lent"   # sans les tests qui peuplent la base complète
ruff check .           # lint
```

Aucune configuration n'est nécessaire : `election/settings_test.py` active
`DEBUG` et pytest-django fabrique une base SQLite temporaire. La suite tourne
hors-ligne, y compris les tests d'intégration.

| Fichier | Ce qu'il vérifie |
|---|---|
| `tests/test_extrapolation.py` | le cœur mathématique sur des données synthétiques dont le résultat est connu analytiquement |
| `tests/test_pipeline.py` | l'enchaînement `peupler_demo` → ACP → extrapolation, et le fait que la projection **corrige** le biais du dépouillement partiel |
| `tests/test_contrat.py` | la forme du dict passé de `donnees.py` aux graphiques — le garde-fou entre les deux voies |
| `tests/test_page_statique.py` | pages éditables servies, 404 sur une URL inconnue, et menu construit depuis la base |

Les mêmes commandes tournent dans la CI (GitHub Actions) sur chaque *pull
request*.

### Répétition générale d'un soir de scrutin

Une soirée entière se rejoue **sans attendre un vrai dimanche de votation** :

```bash
DATE_SCRUTIN=20260927 ./deploiement/repetition_generale.sh
```

Le script copie la base, fabrique une suite d'instantanés de plus en plus
dépouillés avec `create_fake_json_input --fraction`, et enchaîne à chaque tour
les deux commandes du jour J en affichant l'avance et la projection. La base
réelle n'est jamais ouverte en écriture.

À faire avant chaque votation réelle : c'est le premier point de la
[checklist](CHECKLIST_JOUR_J.md).

## Déploiement en conteneur

Pas à pas depuis une machine neuve : [`DEPLOIEMENT.md`](DEPLOIEMENT.md).

## Configuration

Tout passe par l'environnement ou un fichier `.env` non versionné — voir
[`.env.example`](.env.example). Aucune variable n'est requise en local.

| Variable | Défaut | Note |
|---|---|---|
| `DEBUG` | `0` | jamais activé en production |
| `SECRET_KEY` | clé de dev si `DEBUG=1` | **obligatoire** dès que `DEBUG=0` |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | liste séparée par des virgules |
| `DB_PATH` | `votation.sqlite3` | chemin du fichier SQLite |
