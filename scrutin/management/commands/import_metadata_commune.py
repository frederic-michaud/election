import logging

import pandas as pd
from django.core.management.base import BaseCommand

from scrutin.models import Commune

logger = logging.getLogger(__name__)


def  import_commune(path_commune):
    #load data

    df_meta_donnee_commune = pd.read_csv(path_commune)
    for row_commune in df_meta_donnee_commune.itertuples():
        try:
            commune_db = Commune.get_unique_commune_by_ofs(row_commune.CODE_OFS)
            commune_db.langue = row_commune.HR_SPRGEB2016_Name_fr
            commune_db.degre_urbanisation = row_commune.HR_GDETYP2012_L1_Name_fr
            commune_db.save()
        except Exception:
            logger.warning('unable to find info for %s with numero OFS %s',
                           row_commune.Name_fr, row_commune.CODE_OFS)




class Command(BaseCommand):
    help = "Renseigne langue et degré d'urbanisation des communes."

    def add_arguments(self, parser):
        parser.add_argument("csv", nargs="?", default="../data/communes/commune_meta_info.txt")

    def handle(self, *args, **options):
        import_commune(options["csv"])
