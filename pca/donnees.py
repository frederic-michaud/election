"""Contrat de vue des pages ACP : coordonnées et corrélations, sans aucun Plotly."""

import numpy as np

from pca.models import PCAResult
from scrutin.models import ResultatCommunalHistorique, SujetVote

NB_COMPOSANTES = 6


def profils_par_commune():
    """{numéro OFS: [coordonnée 1, …, coordonnée 6]}.

    Une commune sans historique complet est écartée de l'ACP : elle n'a pas de
    profil, et reste donc absente de la carte.
    """
    return {r.commune.numero_ofs: r.get_component(NB_COMPOSANTES)
            for r in PCAResult.objects.select_related('commune')}


def nuage_communes():
    """Les communes dans le plan des axes : noms, survol, et six coordonnées.

    Forme commune aux deux nuages : ``axes[i]`` est la liste des coordonnées de
    toutes les communes sur l'axe i + 1, dans l'ordre de ``noms``.
    """
    profils = PCAResult.objects.select_related('commune', 'commune__canton').order_by('commune__nom')
    noms, survol, coordonnees = [], [], []
    for profil in profils:
        commune = profil.commune
        langue = f" · {commune.langue}" if commune.langue else ""
        noms.append(commune.nom)
        survol.append(f"{commune.nom} · {commune.canton.abreviation}{langue}")
        coordonnees.append(profil.get_component(NB_COMPOSANTES))
    return {"noms": noms, "survol": survol, "axes": [list(a) for a in zip(*coordonnees)]}


def nuage_objets():
    """Les objets de votation dans le plan des axes — le cercle des corrélations.

    Un objet est placé par sa **corrélation** avec chaque composante, calculée
    sur les communes de l'ACP. C'est ce qui donne leur sens aux axes : un objet
    proche du bord du cercle est bien représenté par le plan, et le côté où il
    tombe dit ce que l'axe sépare.

    La corrélation, et non le vecteur propre brut : elle ne dépend pas de
    l'échelle de l'objet, donc tous les objets tiennent dans le même cercle.
    """
    profils = {r.commune_id: r.get_component(NB_COMPOSANTES) for r in PCAResult.objects.all()}

    # `values_list` et non l'ORM complet : instancier les ~200 000 modèles de
    # l'historique prend dix secondes, les lire à plat en prend une.
    par_commune = {}
    for commune_id, sujet_id, oui_, non in ResultatCommunalHistorique.objects.values_list(
            'commune_id', 'sujet_vote_id', 'nombre_oui', 'nombre_non'):
        if commune_id in profils and oui_ + non > 0:
            par_commune.setdefault(commune_id, {})[sujet_id] = oui_ / (oui_ + non)

    sujets = list(SujetVote.objects.filter(
        id__in=ResultatCommunalHistorique.objects.values('sujet_vote')).order_by('id'))
    ids_sujets = [sujet.id for sujet in sujets]
    retenues = [c for c, resultats in par_commune.items() if len(resultats) == len(ids_sujets)]

    oui = np.array([[par_commune[c][s] for s in ids_sujets] for c in retenues])  # communes × objets
    scores = np.array([profils[c] for c in retenues])                            # communes × axes

    nb_objets = len(ids_sujets)
    correlations = np.corrcoef(oui, scores, rowvar=False)[:nb_objets, nb_objets:]
    correlations = np.nan_to_num(correlations)   # un objet voté partout pareil n'a pas de variance

    return {
        "noms": [sujet.nom for sujet in sujets],
        "survol": [f"{sujet.nom} · {sujet.date.year}" for sujet in sujets],
        "axes": [list(colonne) for colonne in correlations.T],
    }
