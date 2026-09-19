"""Contrat de vue des pages ACP : coordonnées et corrélations, sans aucun Plotly."""

import numpy as np

from pca.models import PCAResult
from scrutin.models import ResultatCommunalHistorique, SujetVote

NB_COMPOSANTES = 6


def profils_par_commune():
    """{numéro OFS: [coordonnée 1, …, coordonnée 6]} ; une commune sans profil est absente."""
    return {r.commune.numero_ofs: r.get_component(NB_COMPOSANTES)
            for r in PCAResult.objects.select_related('commune')}


def nuage_communes():
    """Forme commune aux deux nuages : ``axes[i]`` donne la coordonnée de chaque
    point sur l'axe i + 1, dans l'ordre de ``noms`` ; ``cles`` identifie les points
    (ici le numéro OFS, celui des cartes)."""
    profils = PCAResult.objects.select_related('commune', 'commune__canton').order_by('commune__nom')
    noms, cles, survol, coordonnees = [], [], [], []
    for profil in profils:
        commune = profil.commune
        langue = f" · {commune.langue}" if commune.langue else ""
        noms.append(commune.nom)
        cles.append(commune.numero_ofs)
        survol.append(f"{commune.nom} · {commune.canton.abreviation}{langue}")
        coordonnees.append(profil.get_component(NB_COMPOSANTES))
    sujets, oui, scores = _historique()
    return {"noms": noms, "cles": cles, "survol": survol,
            "axes": [list(a) for a in zip(*coordonnees)],
            "variance": _variance_expliquee(oui, _correlations(oui, scores)),
            "periode": _periode(sujets)}


def nuage_objets():
    """Chaque objet placé par sa corrélation avec les axes : indépendante de
    l'échelle de l'objet, elle fait tenir tous les objets dans le cercle unité."""
    sujets, oui, scores = _historique()
    correlations = _correlations(oui, scores)
    return {
        "noms": [sujet.nom for sujet in sujets],
        "cles": [sujet.sujet_id for sujet in sujets],
        "survol": [f"{sujet.nom} · {sujet.date.year}" for sujet in sujets],
        "axes": [list(colonne) for colonne in correlations.T],
        "variance": _variance_expliquee(oui, correlations),
        "periode": _periode(sujets),
    }


def _historique():
    """(sujets, oui, scores) sur les communes de l'ACP à l'historique complet :
    ``oui`` est communes × objets (part de oui), ``scores`` communes × axes."""
    profils = {r.commune_id: r.get_component(NB_COMPOSANTES) for r in PCAResult.objects.all()}

    # values_list : instancier les ~200 000 résultats prendrait dix secondes.
    par_commune = {}
    for commune_id, sujet_id, oui_, non in ResultatCommunalHistorique.objects.values_list(
            'commune_id', 'sujet_vote_id', 'nombre_oui', 'nombre_non'):
        if commune_id in profils and oui_ + non > 0:
            par_commune.setdefault(commune_id, {})[sujet_id] = oui_ / (oui_ + non)

    sujets = list(SujetVote.objects.filter(
        id__in=ResultatCommunalHistorique.objects.values('sujet_vote')).order_by('id'))
    ids_sujets = [sujet.id for sujet in sujets]
    retenues = [c for c, resultats in par_commune.items() if len(resultats) == len(ids_sujets)]

    oui = np.array([[par_commune[c][s] for s in ids_sujets] for c in retenues])
    scores = np.array([profils[c] for c in retenues])
    return sujets, oui, scores


def _correlations(oui, scores):
    """objets × axes ; 0 pour un objet voté partout pareil."""
    nb_objets = oui.shape[1]
    return np.nan_to_num(np.corrcoef(oui, scores, rowvar=False)[:nb_objets, nb_objets:])


def _variance_expliquee(oui, correlations):
    """Part de la variance des votes portée par chaque axe : Σ var·corr² / Σ var.
    Égale à ``explained_variance_ratio_`` de scikit-learn pour une vraie ACP."""
    variances = oui.var(axis=0)
    return [round(float(v), 4) for v in variances @ correlations ** 2 / variances.sum()]


def _periode(sujets):
    dates = [sujet.date for sujet in sujets]
    return {"objets": len(sujets), "debut": min(dates), "fin": max(dates)}
