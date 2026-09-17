"""Contrat de vue de la carte des axes : les coordonnées ACP, sans aucun Plotly."""

from pca.models import PCAResult

NB_COMPOSANTES = 6


def profils_par_commune():
    """{numéro OFS: [coordonnée 1, …, coordonnée 6]}.

    Une commune sans historique complet est écartée de l'ACP : elle n'a pas de
    profil, et reste donc absente de la carte.
    """
    return {r.commune.numero_ofs: r.get_component(NB_COMPOSANTES)
            for r in PCAResult.objects.select_related('commune')}
