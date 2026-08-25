from django.shortcuts import render
from scrutin.models import SujetVote, Extrapolation
import plotly
import plotly.express as px
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
    # Format long (un point = un sujet × une série), construit à la main :
    # pandas ne servait qu'à ce `melt`, et le sortir du chemin web permet à la
    # voie Interface de n'installer que requirements/web.txt.
    ddf = {
        "sujet": sujets_name + sujets_name,
        "pourcentage de oui": (["Déja dépouillés"] * len(currents)
                               + ["Extrapolés"] * len(extrapolations)),
        "value": currents + extrapolations,
    }
    ddf["formated_value"] = [f"{100*v:.1f}%" for v in ddf["value"]]
    histo = plotly.offline.plot(px.bar(ddf, x="sujet",
                                   y = 'value',
                                   color="pourcentage de oui",
                                   barmode="group",
                                   title="",
                                   hover_name="sujet",
                                   text="formated_value"),
                            include_plotlyjs=False,
                            output_type='div')

    # Une carte par objet du scrutin en cours. Les identifiants étaient codés
    # en dur (6, 7, 8) : ceux de septembre 2022.
    all_maps = [carte_api.generate_carte_plot(sujet.id) for sujet in sujets]
    dict_object = {"histo" : histo,"maps" : all_maps, "avance": f"{100*progression:.1f}%", "date": date_plus_recente}
    return render(requete, "home.html", dict_object)