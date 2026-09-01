import datetime

import plotly
import plotly.express as px
from django.shortcuts import render

import carte.API as carte_api
from scrutin.donnees import construire_vue_accueil


def clean_name(name):
        if len(name.split('(')) > 1:
            return name.split('(')[1].split(')')[0]
        return "AVS-TVA"


def histogramme(vue):
    """À déplacer dans scrutin/graphiques.py (voie Interface)."""
    noms = [clean_name(sujet["nom"]) for sujet in vue["sujets"]]
    connus = [sujet["oui_connu"] for sujet in vue["sujets"]]
    extrapoles = [sujet["oui_extrapole"] for sujet in vue["sujets"]]
    ddf = {
        "sujet": noms + noms,
        "pourcentage de oui": ["Déja dépouillés"] * len(connus) + ["Extrapolés"] * len(extrapoles),
        "value": connus + extrapoles,
    }
    ddf["formated_value"] = [f"{100*v:.1f}%" for v in ddf["value"]]
    return plotly.offline.plot(px.bar(ddf, x="sujet",
                                      y='value',
                                      color="pourcentage de oui",
                                      barmode="group",
                                      title="",
                                      hover_name="sujet",
                                      text="formated_value"),
                               include_plotlyjs=False,
                               output_type='div')


def home_view(requete, *args, **kwargs):
    vue = construire_vue_accueil()
    date = datetime.date.fromisoformat(vue["date"]).strftime("%d %b %Y")
    return render(requete, "home.html", {
        "histo": histogramme(vue),
        "maps": [carte_api.generate_carte_plot(sujet["id"]) for sujet in vue["sujets"]],
        "avance": f"{100*vue['avance']:.1f}%",
        "date": date,
    })
