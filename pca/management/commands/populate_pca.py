import numpy as np
from django.core.management.base import BaseCommand

from pca.models import NB_AXES, PCAResult
from scrutin.models import ScrutinAPI


def acp_ponderee(X, poids, nb_composantes=NB_AXES):
    """ACP où chaque commune pèse son nombre d'électeurs : on veut résumer le
    vote des électeurs, pas celui des communes (doc/backtest.md)."""
    centre = X - np.average(X, axis=0, weights=poids)
    _, _, axes = np.linalg.svd(np.sqrt(poids)[:, None] * centre, full_matrices=False)
    return centre @ axes[:nb_composantes].T


def orienter_comme_avant(X, communes, anciennes):
    """Le signe d'un axe est arbitraire : on garde celui du calcul précédent,
    pour que les cartes ne changent pas de couleur à chaque recalcul."""
    lignes = [i for i, commune in enumerate(communes) if commune.id in anciennes]
    if not lignes:
        return X
    precedent = np.array([anciennes[communes[i].id] for i in lignes])
    for axe in range(min(X.shape[1], precedent.shape[1])):
        if X[lignes, axe] @ precedent[:, axe] < 0:
            X[:, axe] *= -1
    return X


def compute_pca():
    (sujets, communes), X = ScrutinAPI.getVotationMatrixWithMetaInfo()
    poids = np.array([commune.nb_voix for commune in communes], dtype=float)
    return communes, acp_ponderee(np.array(X), poids)


class Command(BaseCommand):
    help = "ACP sur l'historique → PCAResult. Remplace tous les PCAResult."

    def handle(self, *args, **options):
        anciennes = dict(PCAResult.objects.values_list('commune_id', 'coordonnees'))
        communes, X = compute_pca()
        X = orienter_comme_avant(X, communes, anciennes)
        PCAResult.objects.all().delete()
        PCAResult.objects.bulk_create(
            PCAResult(commune=commune, coordonnees=[float(x) for x in ligne])
            for commune, ligne in zip(communes, X))
