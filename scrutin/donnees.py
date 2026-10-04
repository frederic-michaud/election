"""Contrat de vue : les données de la page d'accueil, sans aucun Plotly.

Le dict renvoyé est la couture entre la voie Moteur (qui le produit) et la
voie Interface (qui le consomme). Sa forme est figée par
``tests/test_contrat.py`` : on ne la change pas sans mettre le test à jour.
"""

import numpy as np

from scrutin.anomalies import SEUIL_COMMUNES
from scrutin.models import (
    Anomalie,
    Extrapolation,
    Fourchette,
    ResultatCommunalEnCours,
    SujetVote,
)


def resultats_par_commune(sujet):
    """{numéro OFS: {"oui": part de oui ou None, "comptabilise": bool}}.

    ``comptabilise`` distingue le résultat réel de celui écrit par
    ``run_extrapolation`` : c'est ce qui permet aux cartes de séparer réel et
    estimé. ``oui`` est None tant qu'aucune valeur n'a été écrite.
    """
    resultats = {}
    for r in ResultatCommunalEnCours.objects.filter(sujet_vote=sujet).select_related('commune'):
        oui = None
        if r.nombre_oui is not None and r.nombre_non is not None and r.nombre_oui + r.nombre_non > 0:
            oui = r.nombre_oui / (r.nombre_oui + r.nombre_non)
        resultats[r.commune.numero_ofs] = {"oui": oui, "comptabilise": r.comptabilise}
    return resultats


def demi_fourchette(avance, table):
    """Demi-largeur interpolée dans la table de ``Fourchette`` ; None si elle est
    vide : mieux vaut pas de fourchette qu'une fourchette inventée."""
    if not table:
        return None
    avances, largeurs = zip(*table)
    return float(np.interp(avance, avances, largeurs))


def construire_vue_accueil():
    jour = SujetVote.objects.latest('date').date
    table = list(Fourchette.objects.order_by('avance').values_list('avance', 'demi_largeur'))
    vue = {"date": jour.isoformat(), "avance": 0.0, "mise_a_jour": None, "sujets": []}
    instants = []
    for sujet in SujetVote.objects.filter(date=jour).order_by('sujet_id'):
        extra = Extrapolation.objects.filter(sujet_vote=sujet).order_by('-moment_creation').first()
        if extra is not None:  # vrai à partir de SEUIL_COMMUNES communes dépouillées
            vue["avance"] = extra.avance
            instants.append(extra.moment_creation)
        vue["sujets"].append({
            "id": sujet.id,
            "nom": sujet.nom,
            "oui_connu": extra.pourcentage_oui_connu if extra else None,
            "oui_extrapole": extra.pourcentage_oui_extrapole if extra else None,
            # Demi-largeur de la fourchette autour de oui_extrapole, même unité.
            "marge": demi_fourchette(extra.avance, table) if extra else None,
            "communes": resultats_par_commune(sujet),
        })
    if instants:
        vue["mise_a_jour"] = max(instants).isoformat()
    return vue


def construire_vue_anomalies():
    """Les communes du dernier scrutin jugées par ``detecter_anomalies``, de la
    plus grave à la moins grave. ``communes`` est vide tant que le seuil de
    communes dépouillées n'est pas atteint."""
    jour = SujetVote.objects.latest('date').date
    rang = {niveau: i for i, niveau in enumerate(Anomalie.NIVEAUX)}
    anomalies = sorted(Anomalie.objects.filter(date=jour).select_related('commune__canton'),
                       key=lambda a: (-rang[a.niveau], -a.chi2))
    depouillees = (ResultatCommunalEnCours.objects.filter(sujet_vote__date=jour, comptabilise=True)
                   .values('commune').distinct().count())
    return {
        "date": jour.isoformat(),
        "seuil": SEUIL_COMMUNES,
        "depouillees": depouillees,
        "mise_a_jour": max(a.mise_a_jour for a in anomalies).isoformat() if anomalies else None,
        "objets": [{"id": s.id, "nom": s.nom}
                   for s in SujetVote.objects.filter(date=jour).order_by('sujet_id')],
        "communes": [{
            "ofs": a.commune.numero_ofs,
            "nom": a.commune.nom,
            "canton": a.commune.canton.abreviation,
            "niveau": a.niveau,
            "chi2": a.chi2,
            "chi2_corrige": a.chi2_corrige,
            "motifs": a.motifs,
            "correction": a.correction,
            "ecart_bulletins": a.ecart_bulletins,
            "bulletins_habituel": a.bulletins_habituel,
            "signalee_depuis": a.signalee_depuis.isoformat() if a.signalee_depuis else None,
            "note": a.note,
            "centre": a.centre,
            "voisines": a.voisines,
            "historique": a.historique,
            "objets": a.objets,
        } for a in anomalies],
    }
