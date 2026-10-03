from django.core.management.base import BaseCommand
from sklearn.decomposition import PCA

from pca.models import PCAResult
from scrutin.models import ScrutinAPI


def compute_pca():
    (sujets, communes), X = ScrutinAPI.getVotationMatrixWithMetaInfo()
    X_reduced = PCA(n_components=6).fit_transform(X)
    return communes, X_reduced

class Command(BaseCommand):
    help = "ACP sur l'historique → PCAResult. Supprime d'abord tous les PCAResult."

    def handle(self, *args, **options):
        PCAResult.objects.all().delete()
        valid_communes, X = compute_pca()
        entries = []
        for commune, (x1, x2, x3, x4, x5, x6) in zip(valid_communes, X):
            entries.append(PCAResult(commune = commune,
                                     coordinate_1 = x1,
                                     coordinate_2 = x2,
                                     coordinate_3 = x3,
                                     coordinate_4 = x4,
                                     coordinate_5 = x5,
                                     coordinate_6 = x6))
        PCAResult.objects.bulk_create(entries)
