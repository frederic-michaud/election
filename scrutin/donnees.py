"""Contrat de vue : les données de la page d'accueil, sans aucun Plotly.

Le dict renvoyé est la couture entre la voie Moteur (qui le produit) et la
voie Interface (qui le consomme). Sa forme est figée par
``tests/test_contrat.py`` : on ne la change pas sans mettre le test à jour.
"""

from scrutin.models import Extrapolation, ResultatCommunalEnCours, SujetVote


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


def construire_vue_accueil():
    jour = SujetVote.objects.latest('date').date
    vue = {"date": jour.isoformat(), "avance": 0.0, "mise_a_jour": None, "sujets": []}
    instants = []
    for sujet in SujetVote.objects.filter(date=jour).order_by('sujet_id'):
        extra = Extrapolation.objects.filter(sujet_vote=sujet).order_by('-moment_creation').first()
        if extra is not None:  # vrai à partir de sept communes dépouillées
            vue["avance"] = extra.avance
            instants.append(extra.moment_creation)
        vue["sujets"].append({
            "id": sujet.id,
            "nom": sujet.nom,
            "oui_connu": extra.pourcentage_oui_connu if extra else None,
            "oui_extrapole": extra.pourcentage_oui_extrapole if extra else None,
            "communes": resultats_par_commune(sujet),
        })
    if instants:
        vue["mise_a_jour"] = max(instants).isoformat()
    return vue
