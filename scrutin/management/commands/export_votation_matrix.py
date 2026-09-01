import pandas as pd
from django.core.management.base import BaseCommand

from scrutin.models import ScrutinAPI


class Command(BaseCommand):
    help = "Exporte la matrice commune × objet des % de oui en CSV."

    def add_arguments(self, parser):
        parser.add_argument("csv", nargs="?", default="votation_matrix.csv")

    def handle(self, *args, **options):
        (sujets, communes), X = ScrutinAPI.getVotationMatrixWithMetaInfo()
        pd.DataFrame(X, index=communes, columns=sujets).to_csv(options["csv"])


