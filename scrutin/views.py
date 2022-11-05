from django.shortcuts import render
from scrutin.models import SujetVote, Extrapolation
import pandas as pd
import plotly
import plotly.express as px
import locale
import carte.API as carte_api

def clean_name(name):
        if len(name.split('(')) > 1:
            return name.split('(')[1].split(')')[0]
        return "AVS-TVA"


def home_view(requete, *args, **kwargs):
    last_sujet = SujetVote.objects.latest('date')
    sujets = SujetVote.objects.filter(date = last_sujet.date)
    extrapolations = []
    currents = []
    sujets_name = []
    progression = 0
    #locale.setlocale(locale.LC_ALL, 'fr_FR')
    date_plus_recente = last_sujet.date.strftime("%d %b %Y")
    for sujet in sujets:
        extras = Extrapolation.objects.filter(sujet_vote = sujet).order_by("moment_creation")
        if len(extras) == 0:
            raise Exception("No extrapolation for the given subject")
        extra = extras[len(extras)-1]
        extrapolations.append(extra.pourcentage_oui_extrapole)
        currents.append(extra.pourcentage_oui_connu)
        sujets_name.append(clean_name(sujet.nom))
        progression = extra.avance
    df = pd.DataFrame(data={"sujet": sujets_name,
                            'Déja dépouillés': currents,
                            'Extrapolés': extrapolations})
    ddf = df.melt(id_vars= ['sujet'], value_vars=['Déja dépouillés','Extrapolés'], var_name="pourcentage de oui")
    ddf['formated_value'] = ddf['value'].apply(lambda x: f"{100*x:.1f}%")
    print(ddf)
    graph_projections = plotly.offline.plot(px.bar(ddf, x="sujet",
                                   y = 'value',
                                   color="pourcentage de oui",
                                   barmode="group",
                                   title="",
                                   hover_name="sujet",
                                   text="formated_value"),
                            include_plotlyjs=False,
                            output_type='div')
    all_plots = [graph_projections,
                 carte_api.generate_carte_plot(6),
                 carte_api.generate_carte_plot(7),
                 carte_api.generate_carte_plot(8)]

    return render(requete, "home.html", {"plot" : all_plots, "avance": f"{100*progression:.1f}%", "date": date_plus_recente})