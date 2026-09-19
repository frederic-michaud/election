"""Les deux nuages ACP : étiquettes, forme de la figure, et les pages."""

import json

import numpy as np
import pytest

from pca.donnees import _correlations, _variance_expliquee, nuage_communes, nuage_objets
from pca.figures import LARGEUR_ETIQUETTE, OBJETS_PAR_DEFAUT, _etiquette, figure_nuage


def test_l_etiquette_garde_le_nom_d_usage_entre_parentheses():
    nom = ("Initiative populaire « Pour une économie responsable respectant les "
           "limites planétaires (initiative responsabilité) »")
    assert _etiquette(nom) == "initiative responsabilité"
    assert _etiquette("Modification de la loi fédérale sur le service civil (LSC)") == "LSC"


def test_l_etiquette_se_rabat_sur_les_guillemets_puis_sur_la_troncature():
    assert _etiquette("Initiative populaire «Halte à la surpopulation»") == "Halte à la surpopulation"
    long = "Loi fédérale sur l'imposition individuelle des personnes physiques"
    assert _etiquette(long) == long[:LARGEUR_ETIQUETTE - 1] + "…"


def test_la_figure_porte_les_six_axes_et_quatre_traces():
    donnees = {"noms": ["A", "B"], "cles": [1, 2], "survol": ["A", "B"],
               "axes": [[0.1, 0.2]] * 6}
    figure = figure_nuage(donnees)
    assert len(figure.data) == 4                      # points, nommés, recherche, survol
    nuage = figure.layout.meta["nuage"]
    assert len(nuage["axes"]) == 6 and nuage["fixe"] is False   # pas de cercle pour les communes

    objets = figure_nuage(donnees, objets=True)
    assert objets.layout.meta["nuage"]["fixe"] is True
    assert tuple(objets.layout.xaxis.range) == (-1.08, 1.08)


def test_les_points_nommes_d_office():
    """Les communes et objets choisis s'ils sont dans la base, sinon les plus excentrés."""
    axes = [[0.0, 0.9, 0.1, -0.5]] * 6
    communes = {"noms": ["Zürich", "Genève", "X", "Y"], "cles": [261, 6621, 1, 2],
                "survol": ["", "", "", ""], "axes": axes}
    assert figure_nuage(communes).layout.meta["nuage"]["selection"] == [0, 1]

    objets = {"noms": ["a", "b", "c", "d"], "cles": [6440, 1, 2, 3], "survol": ["", "", "", ""], "axes": axes}
    nuage = figure_nuage(objets, objets=True).layout.meta["nuage"]
    assert nuage["selection"] == [0]
    assert nuage["etiquettes"][0] == OBJETS_PAR_DEFAUT[6440]      # le nom d'usage, pas l'intitulé

    inconnus = {**objets, "cles": [7, 8, 9, 10]}
    assert figure_nuage(inconnus, objets=True).layout.meta["nuage"]["selection"][0] == 1   # le plus loin


@pytest.mark.lent
@pytest.mark.django_db
def test_les_deux_nuages_sur_la_base_fictive(base_demo):
    communes = nuage_communes()
    assert len(communes["noms"]) > 2000
    assert len(communes["cles"]) == len(communes["noms"])
    assert all(len(axe) == len(communes["noms"]) for axe in communes["axes"])

    objets = nuage_objets()
    assert len(objets["noms"]) == len(objets["axes"][0]) > 50
    plats = [valeur for axe in objets["axes"] for valeur in axe]
    assert min(plats) >= -1 and max(plats) <= 1          # ce sont des corrélations
    # Le premier axe résume l'essentiel : un objet au moins y est fortement corrélé.
    assert max(abs(v) for v in objets["axes"][0]) > 0.5
    for donnees in (communes, objets):
        assert len(donnees["variance"]) == 6
        assert all(0 <= part <= 1 for part in donnees["variance"])


def test_la_part_de_variance_est_celle_de_l_acp():
    """Sur une vraie ACP, on retrouve les valeurs propres rapportées à la variance
    totale — et quelle que soit l'échelle à laquelle les coordonnées sont stockées."""
    alea = np.random.default_rng(0)
    oui = alea.normal(size=(300, 3)) @ alea.normal(size=(3, 12)) + 0.1 * alea.normal(size=(300, 12))
    centre = oui - oui.mean(axis=0)
    _, valeurs_singulieres, directions = np.linalg.svd(centre, full_matrices=False)
    attendu = valeurs_singulieres ** 2 / (valeurs_singulieres ** 2).sum()
    for echelle in (1, 100):
        scores = echelle * centre @ directions[:6].T
        parts = _variance_expliquee(oui, _correlations(oui, scores))
        assert parts == pytest.approx(attendu[:6], abs=1e-4)


@pytest.mark.lent
@pytest.mark.django_db
def test_les_pages_des_nuages(base_demo, client):
    for url, marque in (("/nuage-acp", "communes"), ("/objets-acp", "objets")):
        html = client.get(url).content.decode()
        assert 'id="axe-x"' in html and 'id="axe-y"' in html
        assert f'data-unite="{marque}"' in html
        assert "tracerNuage(" in html
        figure = json.loads(html.split('<script type="application/json">')[1].split("</script>")[0])
        assert len(figure["layout"]["meta"]["nuage"]["axes"]) == 6
        assert 'id="carte-x"' in html and 'id="carte-y"' in html
        assert "tracerCartesACP();" in html
        carte = json.loads(html.split('<script type="application/json" id="carte-acp">')[1].split("</script>")[0])
        assert len(carte["layout"]["meta"]["axes"]) == 6
        assert html.count("data-variance=") >= 12          # six options par menu

    assert client.get("/pca").status_code == 302
