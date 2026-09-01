"""Forme du contrat de vue entre la voie Moteur et la voie Interface.

Si ``construire_vue_accueil`` change de forme, ce test casse : c'est le
signal qu'il faut mettre à jour ``graphiques.py`` / les templates en face.
"""

import json

import pytest

from scrutin.donnees import construire_vue_accueil
from scrutin.models import Commune, Extrapolation

pytestmark = [pytest.mark.lent, pytest.mark.django_db]


@pytest.fixture(scope="module")
def vue(base_demo):
    return construire_vue_accueil()


def test_la_vue_est_serialisable_en_json(vue):
    assert json.loads(json.dumps(vue))["date"] == vue["date"]


def test_forme_du_contrat(vue):
    assert set(vue) == {"date", "avance", "sujets"}
    assert vue["date"] == Extrapolation.objects.latest("moment_creation").sujet_vote.date.isoformat()
    assert 0 <= vue["avance"] <= 1
    assert len(vue["sujets"]) >= 1
    for sujet in vue["sujets"]:
        assert set(sujet) == {"id", "nom", "oui_connu", "oui_extrapole", "communes"}
        assert isinstance(sujet["id"], int)
        assert isinstance(sujet["nom"], str) and sujet["nom"]
        assert 0 <= sujet["oui_connu"] <= 1
        assert 0 <= sujet["oui_extrapole"] <= 1


def test_communes_par_numero_ofs_avec_drapeau_comptabilise(vue):
    communes = vue["sujets"][0]["communes"]
    assert len(communes) == Commune.objects.count()
    for ofs, resultat in communes.items():
        assert isinstance(ofs, int)
        assert set(resultat) == {"oui", "comptabilise"}
        assert resultat["oui"] is None or 0 <= resultat["oui"] <= 1
        assert isinstance(resultat["comptabilise"], bool)
    # La démo est une soirée en cours : il y a du réel ET de l'estimé.
    drapeaux = {r["comptabilise"] for r in communes.values()}
    assert drapeaux == {True, False}


def test_les_valeurs_viennent_du_dernier_instantane(vue):
    for sujet in vue["sujets"]:
        extra = Extrapolation.objects.filter(sujet_vote_id=sujet["id"]).latest("moment_creation")
        assert sujet["oui_connu"] == extra.pourcentage_oui_connu
        assert sujet["oui_extrapole"] == extra.pourcentage_oui_extrapole


def test_la_page_d_accueil_s_assemble(base_demo, client):
    reponse = client.get("/")
    assert reponse.status_code == 200
    assert "plotly" in reponse.content.decode()
