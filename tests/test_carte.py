"""Le fond de carte : un fichier statique, toutes les communes, et rien dans la figure."""

import csv
import json

import pytest

from carte.API import CONTOURS, EMPRISE, figure_carte

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
    """Le manque du fond précédent : quatorze communes, dont Moutier, sans géométrie."""
    with open(REFERENTIEL) as fichier:
        referentiel = {int(ligne["BfsCode"]) for ligne in csv.DictReader(fichier)}
    assert {entite["properties"]["vogeId"] for entite in contours} == referentiel


@pytest.mark.lent
def test_l_emprise_en_dur_est_celle_du_fichier(contours):
    """``carte.API`` la garde en dur pour ne jamais ouvrir les 5,8 Mo au rendu."""
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
    """Deux garde-fous sur la simplification : la finesse, et l'absence de liseré.

    Une frontière simplifiée deux fois de suite — une fois par commune — ne
    donnerait pas la même ligne, et un liseré blanc apparaîtrait entre voisines.
    On vérifie donc que la grande majorité des arêtes sont partagées au sommet
    près ; ne restent seules que la frontière nationale et les rives des lacs.
    """
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
    """Peints par-dessus les communes : dans la source, une commune riveraine
    s'étend jusqu'au milieu de l'eau."""
    with open(LACS) as fichier:
        lacs = json.load(fichier)["features"]
    assert {"Lac Léman", "Bodensee", "Lago Maggiore"} <= {lac["properties"]["nom"] for lac in lacs}
