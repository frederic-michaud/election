"""Crée cantons, districts et communes depuis le répertoire officiel de l'OFS.

La liste des communes venait de `../data/communes/Communes_actuelles.csv`, un
fichier hors dépôt et sans provenance connue. Elle vient maintenant de l'API
AGVCH (Répertoire officiel des communes de Suisse), sans clé ni inscription,
et le CSV est versionné dans `data/` :

    curl -o data/agvch_communes_2026-01-01.csv \\
      "https://www.agvchapp.bfs.admin.ch/api/communes/snapshot?date=01-01-2026"

Un seul fichier porte les trois niveaux (colonne `Level` : 1 canton,
2 district, 3 commune). Au 01.01.2026 : 26 cantons, 144 districts,
2 110 communes.

**Destructif** : la commande supprime tous les `Canton`, ce qui efface en
cascade districts, communes, résultats historiques et scrutin en cours. C'est
donc la **première** étape du pipeline d'amorçage, jamais une mise à jour à
chaud — rejouer le reste de la chaîne derrière (voir CLAUDE.md, « Pipeline de
données »).
"""

import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction

from scrutin.models import Canton, Commune, District

NIVEAU_CANTON = 1
NIVEAU_DISTRICT = 2
NIVEAU_COMMUNE = 3

# AGVCH nomme les cantons dans leurs langues officielles (« Bern / Berne »,
# « Graubünden / Grigioni / Grischun ») ; le site est francophone et
# peupler_demo sème déjà ces noms-là. L'abréviation, elle, vient du fichier
# (colonne ShortName des lignes de niveau 1).
canton_par_abrev = {"ZH": "Zürich", "BE": "Berne", "LU": "Lucerne", "UR": "Uri", "SZ": "Schwytz", "OW": "Obwald",
                    "NW": "Nidwald", "GL": "Glaris", "ZG": "Zoug", "FR": "Fribourg", "SO": "Soleure",
                    "BS": "Bâle-Ville", "BL": "Bâle-Campagne", "SH": "Schaffhouse",
                    "AR": "Appenzell Rhodes-Extérieures", "AI": "Appenzell Rhodes-Intérieures", "SG": "Saint-Gall",
                    "GR": "Grisons", "AG": "Argovie", "TG": "Thurgovie", "TI": "Tessin", "VD": "Vaud", "VS": "Valais",
                    "NE": "Neuchâtel", "GE": "Genève", "JU": "Jura"}


def import_commune(path_snapshot):
    df = pd.read_csv(path_snapshot)

    # La hiérarchie se chaîne par Parent -> HistoricalCode, jamais par BfsCode.
    # Aucun des deux codes n'est unique en dehors de son niveau : un district et
    # une commune peuvent partager le même BfsCode comme le même HistoricalCode.
    # D'où un dictionnaire de résolution par niveau plutôt qu'un seul global.
    with transaction.atomic():
        Canton.objects.all().delete()  # cascade : districts, communes, historique

        cantons_par_hcode = {}
        for canton_row in df[df["Level"] == NIVEAU_CANTON].itertuples():
            canton = Canton.objects.create(
                nom=canton_par_abrev[canton_row.ShortName],
                abreviation=canton_row.ShortName,
            )
            cantons_par_hcode[canton_row.HistoricalCode] = canton

        districts_par_hcode = {}
        for district_row in df[df["Level"] == NIVEAU_DISTRICT].itertuples():
            district = District.objects.create(
                nom=district_row.Name,
                numero_ofs=district_row.BfsCode,
                canton=cantons_par_hcode[district_row.Parent],
            )
            districts_par_hcode[district_row.HistoricalCode] = district

        for commune_row in df[df["Level"] == NIVEAU_COMMUNE].itertuples():
            district = districts_par_hcode[commune_row.Parent]
            Commune.objects.create(
                nom=commune_row.Name,
                numero_ofs=commune_row.BfsCode,
                district=district,
                canton=district.canton,
            )


class Command(BaseCommand):
    help = "Crée cantons, districts et communes depuis l'export snapshot de l'API AGVCH."

    def add_arguments(self, parser):
        parser.add_argument("csv", nargs="?", default="data/agvch_communes_2026-01-01.csv")

    def handle(self, *args, **options):
        import_commune(options["csv"])
