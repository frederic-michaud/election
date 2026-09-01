import statistics

import geojson
import plotly
import plotly.express as px


def generate_carte_plot(communes):
    """``communes`` : le dict ``sujet["communes"]`` du contrat de vue."""
    with open("data/K4voge_20220501_gf.geojson") as f:
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
        lower_bound_color, upper_bound_color = 0, 100
    else:
        deciles = statistics.quantiles(valeurs_pour_couleur, n=10)
        lower_bound_color, upper_bound_color = deciles[0], deciles[-1]
    div_containing_plot = plotly.offline.plot(px.choropleth_mapbox(dict_properties,
                                                                   geojson=gj,
                                                                   locations='name',
                                                                   color='results',
                                                                   center={"lat": 46.92, "lon": 8.22},
                                                                   zoom=6,
                                                                   # 20 is extremly zoomed... 10 still too much. 7 slightly too much
                                                                   color_continuous_scale="RdYlGn",
                                                                   featureidkey="properties.vogeName",
                                                                   range_color=(lower_bound_color, upper_bound_color),
                                                                   mapbox_style="white-bg",
                                                                   opacity=0.5,
                                                                   labels={'results_formated': 'Resultat',
                                                                           'name': 'Nom'},
                                                                   hover_data={'name': True, 'results_formated': True,
                                                                               'results': False}
                                                                   ),
                                              include_plotlyjs=False,
                                              output_type='div')
    return div_containing_plot

