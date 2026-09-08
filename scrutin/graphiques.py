"""Figures Plotly de la page d'accueil (voie Interface).

Ces fonctions ne consomment que le contrat de vue construit par
`scrutin.donnees` : aucun accès à l'ORM ici.
"""

import plotly
import plotly.express as px


def clean_name(name):
        if len(name.split('(')) > 1:
            return name.split('(')[1].split(')')[0]
        return "AVS-TVA"


def histogramme(vue):
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
