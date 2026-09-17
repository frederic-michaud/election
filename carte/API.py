import functools
import json

import plotly.express as px
import plotly.graph_objects as go

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


def _etendue(valeurs):
    """Demi-étendue de l'échelle de couleur : le 95ᵉ centile des écarts à zéro,
    pour qu'une poignée de communes extrêmes n'écrase pas les nuances du reste."""
    ecarts = sorted(abs(v) for v in valeurs)
    return round(ecarts[int(0.95 * (len(ecarts) - 1))], 2) or 1.0


def _axe(numero, valeurs):
    return {
        "nom": f"Axe {numero}",
        "valeurs": [round(v, 2) for v in valeurs],
        "survol": [f"Axe {numero} : {v:+.2f}".replace(".", ",") for v in valeurs],
        "etendue": _etendue(valeurs),
    }


def figure_carte_acp(profils):
    """Carte des coordonnées ACP par commune, un axe à la fois.

    ``profils`` : le dict de ``pca.donnees.profils_par_commune``. Les axes partent
    tous dans ``layout.meta`` ; ``carte_acp.js`` échange celui qui est affiché.
    """
    gj, emprise = contours()
    noms, coordonnees = [], []
    for entry in gj["features"]:
        profil = profils.get(entry["properties"]["vogeId"])
        if profil is not None:
            noms.append(entry["properties"]["vogeName"])
            coordonnees.append(profil)
    axes = [_axe(numero, colonne) for numero, colonne in enumerate(zip(*coordonnees), start=1)]
    premier = axes[0]
    figure = go.Figure(go.Choroplethmap(
        geojson=gj,
        locations=noms,
        featureidkey="properties.vogeName",
        z=premier["valeurs"],
        hovertext=noms,
        text=premier["survol"],
        hovertemplate="<b>%{hovertext}</b><br>%{text}<extra></extra>",
        coloraxis="coloraxis"))
    charte.habiller_carte(figure, emprise, echelle=(-premier["etendue"], 0, premier["etendue"]))
    figure.update_layout(meta={**figure.layout.meta, "axes": axes})
    return figure
