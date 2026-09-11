"""La carte référence les contours par URL statique au lieu de les incruster."""

import json
import math

import pytest
from django.core.management import call_command

import carte.API as carte_api

SOURCE = "data/K4voge_20220501_gf.geojson"
STATIQUE = "carte/static/carte/communes.geojson"


def sommets(coordonnees):
    if isinstance(coordonnees[0], (int, float)):
        yield coordonnees
    else:
        for c in coordonnees:
            yield from sommets(c)


def test_le_fichier_statique_est_a_jour_par_rapport_a_la_source(tmp_path):
    call_command("alleger_geojson", SOURCE, tmp_path / "communes.geojson", verbosity=0)
    assert (tmp_path / "communes.geojson").read_bytes() == open(STATIQUE, "rb").read()


def test_le_fichier_statique_garde_toutes_les_communes_a_un_metre_pres():
    source = {f["properties"]["vogeId"]: f for f in json.load(open(SOURCE))["features"]}
    allege = {f["properties"]["vogeId"]: f for f in json.load(open(STATIQUE))["features"]}
    assert allege.keys() == source.keys()
    for ofs, f in allege.items():
        assert set(f["properties"]) == {"vogeId", "vogeName"}
        for (x, y), (x0, y0) in zip(sommets(f["geometry"]["coordinates"]),
                                    sommets(source[ofs]["geometry"]["coordinates"])):
            # 1e-5 degré : 1,1 m en latitude, 0,76 m en longitude.
            assert math.hypot((x - x0) * 76_000, (y - y0) * 111_000) < 1


def test_la_carte_contient_l_url_et_pas_les_contours():
    communes = {ofs: {"oui": 0.4 + (ofs % 10) / 50, "comptabilise": True} for ofs in carte_api.nom_par_ofs()}
    div = carte_api.generate_carte_plot(communes)
    assert "communes.geojson" in div  # plotly encode les / en \u002f
    assert "coordinates" not in div
    assert len(div) < 300_000


@pytest.mark.parametrize("communes", [{}, {1: {"oui": None, "comptabilise": False}}])
def test_la_carte_sans_resultat_ne_plante_pas(communes):
    assert "plotly" in carte_api.generate_carte_plot(communes)
