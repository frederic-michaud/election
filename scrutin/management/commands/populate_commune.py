"""Crée cantons, districts et communes depuis le répertoire officiel de l'OFS.

**Destructif** : la commande supprime tous les `Canton`, ce qui efface en
cascade districts, communes, résultats historiques et scrutin en cours.
"""

import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction

from scrutin.models import Canton, Commune, District

# Numérotation OFS officielle des cantons (colonne `CantonId`), et les noms
# français que sème déjà `peupler_demo`.
CANTONS = {
    1: ("ZH", "Zürich"), 2: ("BE", "Berne"), 3: ("LU", "Lucerne"),
    4: ("UR", "Uri"), 5: ("SZ", "Schwytz"), 6: ("OW", "Obwald"),
    7: ("NW", "Nidwald"), 8: ("GL", "Glaris"), 9: ("ZG", "Zoug"),
    10: ("FR", "Fribourg"), 11: ("SO", "Soleure"), 12: ("BS", "Bâle-Ville"),
    13: ("BL", "Bâle-Campagne"), 14: ("SH", "Schaffhouse"),
    15: ("AR", "Appenzell Rhodes-Extérieures"),
    16: ("AI", "Appenzell Rhodes-Intérieures"), 17: ("SG", "Saint-Gall"),
    18: ("GR", "Grisons"), 19: ("AG", "Argovie"), 20: ("TG", "Thurgovie"),
    21: ("TI", "Tessin"), 22: ("VD", "Vaud"), 23: ("VS", "Valais"),
    24: ("NE", "Neuchâtel"), 25: ("GE", "Genève"), 26: ("JU", "Jura"),
}


def import_commune(path_niveaux):
    df = pd.read_csv(path_niveaux)

    with transaction.atomic():
        Canton.objects.all().delete()  # cascade : districts, communes, historique

        cantons = {}
        for id_canton in sorted(df["CantonId"].unique()):
            abreviation, nom = CANTONS[id_canton]
            cantons[id_canton] = Canton.objects.create(nom=nom, abreviation=abreviation)

        districts = {}
        for district_row in df.drop_duplicates("DistrictId").itertuples():
            districts[district_row.DistrictId] = District.objects.create(
                nom=district_row.District,
                code_historique=district_row.DistrictId,
                canton=cantons[district_row.CantonId],
            )

        for commune_row in df.itertuples():
            Commune.objects.create(
                nom=commune_row.Name,
                numero_ofs=commune_row.BfsCode,
                district=districts[commune_row.DistrictId],
                canton=cantons[commune_row.CantonId],
            )


class Command(BaseCommand):
    help = "Crée cantons, districts et communes depuis l'export levels de l'API AGVCH."

    def add_arguments(self, parser):
        parser.add_argument("csv", nargs="?", default="data/agvch_niveaux_2026-01-01.csv")

    def handle(self, *args, **options):
        import_commune(options["csv"])
