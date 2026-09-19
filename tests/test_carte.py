"""Les cartes : fond statique, toutes les communes, et rien des contours dans la figure."""

import csv
import json

import pytest

from carte.API import CONTOURS, EMPRISE, figure_carte, figure_carte_acp

FICHIER = "carte/static/carte/communes.geojson"
LACS = "carte/static/carte/lacs.geojson"
REFERENTIEL = "data/agvch_niveaux_2026-01-01.csv"


@pytest.fixture(scope="module")
def contours():
    with open(FICHIER) as fichier:
        return json.load(fichier)["features"]


def test_la_figure_porte_l_url_des_contours_et_pas_les_contours():
    figure = figure_carte({1: {"oui": 0.55, "comptabilise": True},
                           2: {"oui": None, "comptabilise": False}})
    json_figure = figure.to_json()
    assert CONTOURS in figure.data[0].geojson
    assert "coordinates" not in json_figure
    # Une commune sans résultat n'est pas dessinée, mais ne fait pas tomber la carte.
    assert figure.data[0].locations == (1,)
    assert len(json_figure) < 100_000


@pytest.mark.lent
def test_toutes_les_communes_du_referentiel_ont_un_contour(contours):
    with open(REFERENTIEL) as fichier:
        referentiel = {int(ligne["BfsCode"]) for ligne in csv.DictReader(fichier)}
    assert {entite["properties"]["vogeId"] for entite in contours} == referentiel


@pytest.mark.lent
def test_l_emprise_en_dur_est_celle_du_fichier(contours):
    def points(coordonnees):
        if isinstance(coordonnees[0], (int, float)):
            yield coordonnees
        else:
            for c in coordonnees:
                yield from points(c)

    lon, lat = zip(*(p for e in contours for p in points(e["geometry"]["coordinates"])))
    assert EMPRISE == ((min(lon), min(lat)), (max(lon), max(lat)))


@pytest.mark.lent
def test_les_contours_sont_detailles_et_partagent_leurs_frontieres(contours):
    """Assez de sommets, et des frontières communes identiques des deux côtés
    (sinon, liseré blanc entre voisines) : seules la frontière nationale et les
    rives des lacs n'appartiennent qu'à une commune."""
    aretes = {}
    for entite in contours:
        coordonnees = entite["geometry"]["coordinates"]
        anneaux = (coordonnees if entite["geometry"]["type"] == "Polygon"
                   else [anneau for polygone in coordonnees for anneau in polygone])
        for anneau in anneaux:
            for depart, arrivee in zip(anneau, anneau[1:]):
                cle = (tuple(depart), tuple(arrivee)) if depart < arrivee else (tuple(arrivee), tuple(depart))
                aretes[cle] = aretes.get(cle, 0) + 1

    seules = sum(1 for compte in aretes.values() if compte == 1)
    assert sum(aretes.values()) / len(contours) > 100     # ~140 sommets par commune
    assert seules / len(aretes) < 0.6


def test_les_lacs_sont_a_part():
    with open(LACS) as fichier:
        lacs = json.load(fichier)["features"]
    assert {"Lac Léman", "Bodensee", "Lago Maggiore"} <= {lac["properties"]["nom"] for lac in lacs}


def test_la_carte_acp_porte_les_six_axes_et_leur_echelle():
    # Le premier axe vaut 0, 1, … 19 ; l'échelle est bornée au 95ᵉ centile.
    profils = {ofs: [float(ofs - 1), 0, 0, 0, 0, 0] for ofs in range(1, 21)}
    figure = figure_carte_acp(profils)
    axes = figure.layout.meta["axes"]
    assert [axe["nom"] for axe in axes] == [f"Axe {i}" for i in range(1, 7)]
    assert figure.data[0].z == tuple(axes[0]["valeurs"])
    assert axes[0]["survol"][1] == "Axe 1 : +1,00"
    axe_couleur = figure.layout.coloraxis
    assert (axe_couleur.cmin, axe_couleur.cmid, axe_couleur.cmax) == (-18.0, 0, 18.0)
