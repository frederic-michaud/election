import functools
import json

import plotly.express as px

from scrutin import charte

CONTOURS = "data/K4voge_20220501_gf.geojson"


def _arrondir(coordonnees):
    """5 décimales, soit environ 1 m : le fichier en a 16, qui alourdissent la page."""
    if isinstance(coordonnees[0], (int, float)):
        return [round(c, 5) for c in coordonnees]
    return [_arrondir(c) for c in coordonnees]


def _points(coordonnees):
    if isinstance(coordonnees[0], (int, float)):
        yield coordonnees
    else:
        for c in coordonnees:
            yield from _points(c)


@functools.cache
def contours():
    """Le GeoJSON communal et son emprise ((lon min, lat min), (lon max, lat max))."""
    with open(CONTOURS) as f:
        gj = json.load(f)
    for feature in gj["features"]:
        feature["geometry"]["coordinates"] = _arrondir(feature["geometry"]["coordinates"])
    lon, lat = zip(*(p for f in gj["features"] for p in _points(f["geometry"]["coordinates"])))
    return gj, ((min(lon), min(lat)), (max(lon), max(lat)))


def figure_carte(communes):
    """Carte WebGL des résultats par commune, tracée par ``carte/static/carte/cartes.js``.

    ``communes`` : le dict ``sujet["communes"]`` du contrat de vue.
    """
    gj, emprise = contours()
    noms, oui, survol = [], [], []
    for entry in gj["features"]:
        resultat = communes.get(entry["properties"]["vogeId"])
        if resultat is not None and resultat["oui"] is not None:
            noms.append(entry["properties"]["vogeName"])
            oui.append(resultat["oui"] * 100)
            survol.append(f"{resultat['oui'] * 100:.1f} %".replace(".", ","))
    figure = px.choropleth_map({"commune": noms, "oui": oui, "part de oui": survol},
                               geojson=gj,
                               locations="commune",
                               featureidkey="properties.vogeName",
                               color="oui",
                               hover_name="commune",
                               hover_data={"commune": False, "oui": False, "part de oui": True})
    return charte.habiller_carte(figure, emprise)
