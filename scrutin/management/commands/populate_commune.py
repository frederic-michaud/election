"""Crée cantons, districts et communes depuis le répertoire officiel de l'OFS.

La liste des communes venait de `../data/communes/Communes_actuelles.csv`, un
fichier hors dépôt et sans provenance connue. Elle vient maintenant de l'API
AGVCH (Répertoire officiel des communes de Suisse), sans clé ni inscription,
et le CSV est versionné dans `data/` :

    curl -o data/agvch_niveaux_2026-01-01.csv \\
      "https://www.agvchapp.bfs.admin.ch/api/communes/levels?date=01-01-2026"

Une ligne par commune, la hiérarchie déjà jointe : `BfsCode` et `Name` pour la
commune, `DistrictId` et `District` pour son district, `CantonId` et `Canton`
pour son canton. Au 01.01.2026 : 26 cantons, 144 districts, 2 110 communes.
C'est le même fichier que lit `import_metadata_commune`, qui y prend en plus la
langue et le degré d'urbanisation.

Deux colonnes manquent au fichier, sans conséquence :

- l'**abréviation** du canton, reconstituée par `CANTONS` ci-dessous — le site
  est francophone, et AGVCH nomme les cantons dans toutes leurs langues
  officielles (« Bern / Berne », « Graubünden / Grigioni / Grischun ») ;
- le **numéro OFS du district** : `DistrictId` est son identifiant
  d'historisation. D'où `District.code_historique`, qui ne sert qu'à rattacher
  les communes à leur district au moment de l'import. Les résultats de votation
  sont rattachés à des communes, jamais à des districts.

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
