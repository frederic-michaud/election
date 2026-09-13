"""La carte choroplèthe communale (voie Interface).

Transposition de la carte de la maquette D′ : projection SVG plutôt que
Mapbox, échelle divergente ancrée à 50 %, sans barre de couleur — la carte
répond à « où ça penche oui, où ça penche non », pas à « combien exactement ».

Le choix de la projection SVG est acté (Partie 7.2) : ni WebGL, ni fond de
carte externe, donc imprimable et capturable, et sans la dépréciation de
`choropleth_mapbox`.
"""

import functools
import json
from pathlib import Path

import plotly.express as px

from scrutin.charte import (
    CONTOUR,
    DEMI_ETENDUE,
    ECHELLE_DIVERGENTE,
    OPACITE,
    PANNEAU,
    appliquer_charte,
)

GEOJSON_COMMUNES = Path("data/K4voge_20220501_gf.geojson")

ETIQUETTES = {"resultat_formate": "Résultat", "nom": "Commune"}
SURVOL = {"nom": True, "resultat_formate": True, "resultat": False}


@functools.cache
def contours():
    """Les contours communaux, lus une fois pour toutes les cartes de la page."""
    with open(GEOJSON_COMMUNES) as fichier:
        return json.load(fichier)


@functools.cache
def emprise():
    """`(lon_min, lat_min, lon_max, lat_max)` des contours, plus une marge.

    La maquette la calculait dans le navigateur ; ici c'est fait en Python,
    une seule fois. Il le faudra de toute façon le jour où les contours
    seront servis par URL : la page ne les aura plus sous la main au moment
    de tracer.
    """
    lon_min = lat_min = float("inf")
    lon_max = lat_max = float("-inf")

    def parcourir(coordonnees):
        nonlocal lon_min, lat_min, lon_max, lat_max
        if isinstance(coordonnees[0], (int, float)):
            lon, lat = coordonnees[0], coordonnees[1]
            lon_min, lon_max = min(lon_min, lon), max(lon_max, lon)
            lat_min, lat_max = min(lat_min, lat), max(lat_max, lat)
            return
        for partie in coordonnees:
            parcourir(partie)

    for element in contours()["features"]:
        parcourir(element["geometry"]["coordinates"])
    marge = 0.005 * (lon_max - lon_min)
    return lon_min - marge, lat_min - marge, lon_max + marge, lat_max + marge


def _colonnes(communes):
    """Les colonnes attendues par `px`, dans l'ordre des contours."""
    noms, resultats = [], []
    for element in contours()["features"]:
        resultat = communes.get(element["properties"]["vogeId"])
        if resultat is not None and resultat["oui"] is not None:
            noms.append(element["properties"]["vogeName"])
            resultats.append(resultat["oui"] * 100)
    return {
        "nom": noms,
        "resultat": resultats,
        "resultat_formate": [f"{valeur:.1f} %".replace(".", ",") for valeur in resultats],
    }


def carte(communes):
    """`communes` : le dict `sujet["communes"]` du contrat de vue."""
    figure = px.choropleth(
        _colonnes(communes),
        geojson=contours(),
        locations="nom",
        color="resultat",
        featureidkey="properties.vogeName",
        color_continuous_scale=ECHELLE_DIVERGENTE,
        # Bornes symétriques : le milieu de l'échelle tombe exactement sur la
        # majorité. L'ancienne échelle, calée sur les déciles, avait un milieu
        # qui ne voulait rien dire.
        range_color=(50 - DEMI_ETENDUE, 50 + DEMI_ETENDUE),
        labels=ETIQUETTES,
        hover_data=SURVOL,
    )
    figure.update_traces(marker={"opacity": OPACITE, "line": {"width": CONTOUR, "color": PANNEAU}})
    figure.update_coloraxes(showscale=False)
    lon_min, lat_min, lon_max, lat_max = emprise()
    figure.update_geos(
        visible=False,
        showframe=False,
        showcoastlines=False,
        bgcolor="rgba(0,0,0,0)",
        # Par défaut Plotly projette en équirectangulaire : à 47° nord, la
        # Suisse en sort une fois et demie trop large. Mercator rend les
        # proportions, et sur un pays de cette taille sa déformation ne se
        # voit pas.
        projection={"type": "mercator"},
        # `fitbounds` calerait le pays dans le cadre carré de la projection
        # entière : il y flotterait, avec une bande vide de chaque côté.
        # Borner les axes à l'emprise des contours donne au cadre les
        # proportions du pays, et la carte remplit son panneau.
        fitbounds=False,
        lonaxis={"range": [lon_min, lon_max]},
        lataxis={"range": [lat_min, lat_max]},
    )
    # Pas de hauteur : c'est l'`aspect-ratio` du conteneur qui la donne, donc
    # la largeur du panneau.
    return appliquer_charte(figure)
