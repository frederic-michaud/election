"""Les deux nuages ACP : étiquettes, forme de la figure, et les pages."""

import json

import pytest

from pca.donnees import nuage_communes, nuage_objets
from pca.figures import LARGEUR_ETIQUETTE, _etiquette, figure_nuage


def test_l_etiquette_garde_le_nom_d_usage_entre_parentheses():
    nom = ("Initiative populaire « Pour une économie responsable respectant les "
           "limites planétaires (initiative responsabilité) »")
    assert _etiquette(nom) == "initiative responsabilité"
    assert _etiquette("Modification de la loi fédérale sur le service civil (LSC)") == "LSC"


def test_l_etiquette_se_rabat_sur_les_guillemets_puis_sur_la_troncature():
    assert _etiquette("Initiative populaire «Halte à la surpopulation»") == "Halte à la surpopulation"
    long = "Loi fédérale sur l'imposition individuelle des personnes physiques"
    assert _etiquette(long) == long[:LARGEUR_ETIQUETTE - 1] + "…"


def test_la_figure_porte_les_six_axes_et_trois_traces():
    donnees = {"noms": ["A", "B"], "survol": ["A", "B"],
               "axes": [[0.1, 0.2]] * 6}
    figure = figure_nuage(donnees)
    assert len(figure.data) == 3                      # points, extrêmes, recherche
    nuage = figure.layout.meta["nuage"]
    assert len(nuage["axes"]) == 6
    assert (nuage["extremes"], nuage["fixe"]) == (0, False)   # pas de cercle pour les communes

    objets = figure_nuage(donnees, objets=True).layout.meta["nuage"]
    assert objets["extremes"] > 0 and objets["fixe"] is True
    assert tuple(figure_nuage(donnees, objets=True).layout.xaxis.range) == (-1.08, 1.08)


@pytest.mark.lent
@pytest.mark.django_db
def test_les_deux_nuages_sur_la_base_fictive(base_demo):
    communes = nuage_communes()
    assert len(communes["noms"]) > 2000
    assert all(len(axe) == len(communes["noms"]) for axe in communes["axes"])

    objets = nuage_objets()
    assert len(objets["noms"]) == len(objets["axes"][0]) > 50
    plats = [valeur for axe in objets["axes"] for valeur in axe]
    assert min(plats) >= -1 and max(plats) <= 1          # ce sont des corrélations
    # Le premier axe résume l'essentiel : un objet au moins y est fortement corrélé.
    assert max(abs(v) for v in objets["axes"][0]) > 0.5


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

    assert client.get("/pca").status_code == 302      # ancienne adresse du nuage
