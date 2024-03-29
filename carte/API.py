import plotly.express as px
from scrutin.models import ScrutinAPI
import plotly
import geojson
import numpy as np


def generate_carte_plot(id_scrutin):
    with open("data/K4voge_20220501_gf.geojson") as f:
        gj = geojson.load(f)
    all_cities = []
    all_results = []
    oui_per_commune_id = ScrutinAPI.get_percentage_oui_all_commune(id_scrutin)
    for entry in gj["features"]:
        if entry['properties']['vogeId'] in oui_per_commune_id.keys():
            all_cities.append(entry["properties"]['vogeName'])
            all_results.append(oui_per_commune_id[entry['properties']['vogeId']] * 100)
    all_results_formated = list(map(lambda x: f'{x:.2f} %', all_results))
    dict_properties = {'name': all_cities,
                       'results': all_results,
                       'results_formated': all_results_formated}
    array_for_color = np.array(dict_properties['results'])
    array_for_color = array_for_color[array_for_color > 0]
    lower_bound_color = np.percentile(array_for_color, 10)
    upper_bound_color = np.percentile(array_for_color, 90)
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

