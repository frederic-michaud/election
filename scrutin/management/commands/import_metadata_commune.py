"""Renseigne langue et degré d'urbanisation depuis le répertoire de l'OFS.

Ces métadonnées venaient de `../data/communes/commune_meta_info.txt`, hors
dépôt et sans provenance connue. Elles viennent maintenant de l'API AGVCH,
dont le CSV est versionné dans `data/` — le **même fichier** que lit
`populate_commune`, qui y prend la hiérarchie des communes :

    curl -o data/agvch_niveaux_2026-01-01.csv \\
      "https://www.agvchapp.bfs.admin.ch/api/communes/levels?date=01-01-2026"

Une ligne par commune, appariée par `BfsCode` — le `numero_ofs` de la base.
À lancer après `populate_commune`, qui sème les communes que ce fichier
complète.
"""

import logging

import pandas as pd
from django.core.management.base import BaseCommand

from scrutin.models import Commune

logger = logging.getLogger(__name__)

LANGUES = {1: "allemand", 2: "français", 3: "italien", 4: "romanche"}

# Échelle officielle à trois degrés (DEGURB2021). peupler_demo n'en écrit
# encore que deux (urbain/rural) — voir PLAN_MODERNISATION.md, A6.
DEGRES_URBANISATION = {1: "urbain", 2: "intermédiaire", 3: "rural"}


def import_commune(path_niveaux):
    df = pd.read_csv(path_niveaux)
    for row_commune in df.itertuples():
        try:
            commune_db = Commune.get_unique_commune_by_ofs(row_commune.BfsCode)
        except Exception:
            logger.warning('unable to find info for %s with numero OFS %s',
                           row_commune.Name, row_commune.BfsCode)
            continue
        commune_db.langue = LANGUES[row_commune.SPRGEB2020]
        commune_db.degre_urbanisation = DEGRES_URBANISATION[row_commune.DEGURB2021]
        commune_db.save()


class Command(BaseCommand):
    help = "Renseigne langue et degré d'urbanisation depuis l'export levels de l'API AGVCH."

    def add_arguments(self, parser):
        parser.add_argument("csv", nargs="?", default="data/agvch_niveaux_2026-01-01.csv")

    def handle(self, *args, **options):
        import_commune(options["csv"])
