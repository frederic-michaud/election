from django.http import HttpResponse
from django.shortcuts import render
from scrutin.models import SujetVote
from scrutin.extrapolation import get_extrapolation
import pandas as pd
import plotly
import plotly.express as px


def clean_name(name):
    return name.split('(')[1].split(')')[0]
# Create your views here.
def home_view(requete, *args, **kwargs):
    last_sujet = SujetVote.objects.latest('date')
    sujets = SujetVote.objects.filter(date = last_sujet.date)
    extrapolations = []
    currents = []
    sujets_name = []
    for sujet in sujets:
        current, extrapolation = get_extrapolation(sujet)
        extrapolations.append(extrapolation)
        currents.append(current)
        sujets_name.append(clean_name(sujet.nom))
    df = pd.DataFrame(data={"sujet": sujets_name,
                            'Current': currents,
                            'Extrapolated': extrapolations})
    ddf = df.melt(id_vars= ['sujet'], value_vars=['Current','Extrapolated'])
    print(ddf)
    a = plotly.offline.plot(px.bar(ddf, x="sujet",
                                   y = 'value',
                                   color='variable',
                                   barmode="group",
                                   title="",
                 width=800, height=800),
                            include_plotlyjs=False,
                            output_type='div')
    return render(requete, "home.html", {"plot" : a})