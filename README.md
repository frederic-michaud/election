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
python manage.py runserver
```

La base est **SQLite** (`votation.sqlite3` à la racine) — rien à installer.

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

**Fictives** (usage quotidien) : à venir, `python manage.py peupler_demo`.
Construit une base à l'échelle réelle (~2 130 communes) sans aucun
téléchargement.

**Réelles** : voir le pipeline d'import décrit dans [`CLAUDE.md`](CLAUDE.md).

## Configuration

Tout passe par l'environnement ou un fichier `.env` non versionné — voir
[`.env.example`](.env.example). Aucune variable n'est requise en local.

| Variable | Défaut | Note |
|---|---|---|
| `DEBUG` | `0` | jamais activé en production |
| `SECRET_KEY` | clé de dev si `DEBUG=1` | **obligatoire** dès que `DEBUG=0` |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | liste séparée par des virgules |
| `DB_PATH` | `votation.sqlite3` | chemin du fichier SQLite |

## Organisation du travail

Le projet se développe sur deux voies parallèles, **Moteur** (maths, backend,
infra — branches `moteur/…`) et **Interface** (design, frontend, données —
branches `interface/…`), séparées par une couture données / présentation.
Détail dans [`CLAUDE.md`](CLAUDE.md) et `PLAN_MODERNISATION.md` (Partie 0).
