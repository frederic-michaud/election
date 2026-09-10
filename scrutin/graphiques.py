"""Figures Plotly de la page d'accueil (voie Interface).

Ces fonctions ne consomment que le contrat de vue construit par
`scrutin.donnees` : aucun accès à l'ORM ici.

Chaque figure existe sous deux formes : ``figure_*`` renvoie l'objet Plotly
(ce que la maquette statique exporte en JSON, voir ``maquette/``), et la
fonction sans préfixe l'enrobe en ``<div>`` pour les gabarits Django. Les deux
partagent le même code : la maquette et le site ne peuvent pas diverger.
"""

import plotly
import plotly.express as px


def en_div(figure):
    """Le ``<div>`` autonome qu'attendent les gabarits (sans plotly.js)."""
    return plotly.offline.plot(figure, include_plotlyjs=False, output_type='div')


def clean_name(name):
        if len(name.split('(')) > 1:
            return name.split('(')[1].split(')')[0]
        return "AVS-TVA"


def figure_histogramme(vue):
    noms = [clean_name(sujet["nom"]) for sujet in vue["sujets"]]
    connus = [sujet["oui_connu"] for sujet in vue["sujets"]]
    extrapoles = [sujet["oui_extrapole"] for sujet in vue["sujets"]]
    ddf = {
        "sujet": noms + noms,
        "pourcentage de oui": ["Déja dépouillés"] * len(connus) + ["Extrapolés"] * len(extrapoles),
        "value": connus + extrapoles,
    }
    ddf["formated_value"] = [f"{100*v:.1f}%" for v in ddf["value"]]
    return px.bar(ddf, x="sujet",
                  y='value',
                  color="pourcentage de oui",
                  barmode="group",
                  title="",
                  hover_name="sujet",
                  text="formated_value")


def histogramme(vue):
    return en_div(figure_histogramme(vue))
