"""Cartes choroplèthes communales (voie Interface).

Deux variantes de la même carte, à comparer pendant la refonte graphique
(`PLAN_MODERNISATION.md`, Partie 7.2) :

- ``figure_carte`` — Mapbox, ce que le site rend aujourd'hui. Exige WebGL.
- ``figure_carte_svg`` — projection SVG (``px.choropleth``), sans WebGL ni
  fond de carte : imprimable, capturable partout, et sans la dépréciation de
  ``choropleth_mapbox``.

``generate_carte_plot`` reste l'entrée des vues et n'a pas changé de rendu.
"""

import statistics

import geojson
import plotly.express as px

from scrutin.graphiques import en_div

GEOJSON_COMMUNES = "data/K4voge_20220501_gf.geojson"


def _donnees_carte(communes, chemin_geojson):
    """Le GeoJSON et les colonnes attendues par ``px``, plus les bornes."""
    with open(chemin_geojson or GEOJSON_COMMUNES) as f:
        gj = geojson.load(f)
    all_cities = []
    all_results = []
    for entry in gj["features"]:
        resultat = communes.get(entry['properties']['vogeId'])
        if resultat is not None and resultat["oui"] is not None:
            all_cities.append(entry["properties"]['vogeName'])
            all_results.append(resultat["oui"] * 100)
    all_results_formated = list(map(lambda x: f'{x:.2f} %', all_results))
    dict_properties = {'name': all_cities,
                       'results': all_results,
                       'results_formated': all_results_formated}
    # Bornes de l'échelle de couleur aux 1er et 9e déciles. numpy ne servait
    # qu'à ça : `statistics` suffit, et la voie Interface n'a plus besoin de la
    # pile scientifique pour afficher une carte.
    valeurs_pour_couleur = [v for v in dict_properties['results'] if v > 0]
    if len(valeurs_pour_couleur) < 2:
        # Aucun résultat pour ce scrutin : échelle neutre plutôt qu'un plantage.
        bornes = (0, 100)
    else:
        deciles = statistics.quantiles(valeurs_pour_couleur, n=10)
        bornes = (deciles[0], deciles[-1])
    return gj, dict_properties, bornes


ETIQUETTES = {'results_formated': 'Resultat', 'name': 'Nom'}
SURVOL = {'name': True, 'results_formated': True, 'results': False}


def figure_carte(communes, chemin_geojson=None):
    """``communes`` : le dict ``sujet["communes"]`` du contrat de vue.

    Renvoie la figure Plotly ; ``generate_carte_plot`` l'enrobe en ``<div>``.
    """
    gj, dict_properties, bornes = _donnees_carte(communes, chemin_geojson)
    return px.choropleth_mapbox(dict_properties,
                                geojson=gj,
                                locations='name',
                                color='results',
                                center={"lat": 46.92, "lon": 8.22},
                                zoom=6,
                                # 20 is extremly zoomed... 10 still too much. 7 slightly too much
                                color_continuous_scale="RdYlGn",
                                featureidkey="properties.vogeName",
                                range_color=bornes,
                                mapbox_style="white-bg",
                                opacity=0.5,
                                labels=ETIQUETTES,
                                hover_data=SURVOL)


def figure_carte_svg(communes, chemin_geojson=None):
    """La même carte, en projection SVG : ni WebGL, ni fond de carte."""
    gj, dict_properties, bornes = _donnees_carte(communes, chemin_geojson)
    figure = px.choropleth(dict_properties,
                           geojson=gj,
                           locations='name',
                           color='results',
                           color_continuous_scale="RdYlGn",
                           featureidkey="properties.vogeName",
                           range_color=bornes,
                           labels=ETIQUETTES,
                           hover_data=SURVOL)
    figure.update_geos(fitbounds="locations", visible=False)
    return figure


def generate_carte_plot(communes):
    return en_div(figure_carte(communes))
