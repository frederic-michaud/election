import plotly.express as px
from django.shortcuts import render
import plotly
from pca.models import PCAResult
def get_hover_info(commune):
    return f'{commune.nom} \n {commune.canton.abreviation}'

def get_color(commune):
    return f'{commune.langue}'

def pca_view(requete, *args, **kwargs):
    results = PCAResult.objects.all()
    x = [result.coordinate_1 for result in results]
    y = [result.coordinate_2 for result in results]
    name = [get_hover_info(result.commune) for result in results]
    color = [get_color(result.commune) for result in results]
    a = plotly.offline.plot(px.scatter(x=x, y=y, hover_name = name,
                                       hover_data = None, color=color,
                 width=800, height=800),
                            include_plotlyjs=False,
                            output_type='div')
    return render(requete, "home.html", {'plot':a})