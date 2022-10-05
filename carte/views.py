import plotly.express as px
from scrutin.models import ScrutinAPI
from django.shortcuts import render
import plotly
import geojson
import numpy as np

def carte_view(requete, *args, **kwargs):
    with open("data/switzerland2.geojson") as f:
        gj = geojson.load(f)
    all_cities = []
    all_cities_id = []
    for entry in gj["features"]:
        all_cities.append(entry["properties"]['NAME'])
        all_cities_id.append(entry["properties"]['BFS_NUMMER'])
    oui_per_commune_id = ScrutinAPI.get_percentage_oui_all_commune(6)
    d = {'name' : all_cities,
         'results':list(map(lambda x: oui_per_commune_id.get(x, 0), all_cities_id))}
    array_for_color = np.array(d['results'])
    array_for_color = array_for_color[array_for_color > 0]
    lower_bound_color = np.percentile(array_for_color,10)
    upper_bound_color = np.percentile(array_for_color,90)
    a = plotly.offline.plot(px.choropleth_mapbox(d, geojson=gj, locations='name', color='results',
                           color_continuous_scale="Viridis",
                           featureidkey="properties.NAME",
                           range_color=(lower_bound_color, upper_bound_color),
                           mapbox_style="carto-positron",
                           zoom=3,
                           opacity=0.5,
                           labels={'results':'Resultat', 'name' : 'Nom'}
                          ),
                            include_plotlyjs=False,
                            output_type='div')

    return render(requete, "home.html", {'plot':a})