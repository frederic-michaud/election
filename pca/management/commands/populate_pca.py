import numpy as np
from django.core.management.base import BaseCommand

from pca.models import PCAResult
from scrutin.models import ScrutinAPI


def acp_ponderee(X, poids, nb_composantes=6):
    """ACP où chaque commune pèse son nombre d'électeurs : on veut résumer le
    vote des électeurs, pas celui des communes (doc/backtest.md)."""
    centre = X - np.average(X, axis=0, weights=poids)
    _, _, axes = np.linalg.svd(np.sqrt(poids)[:, None] * centre, full_matrices=False)
    return centre @ axes[:nb_composantes].T


def compute_pca():
    (sujets, communes), X = ScrutinAPI.getVotationMatrixWithMetaInfo()
    poids = np.array([commune.nb_voix for commune in communes], dtype=float)
    return communes, acp_ponderee(np.array(X), poids)

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
