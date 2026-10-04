from django.shortcuts import render

import carte.API as carte_api
from scrutin.donnees import construire_vue_accueil, construire_vue_anomalies
from scrutin.graphiques import accueil, en_json
from scrutin.graphiques_anomalies import page_anomalies


def home_view(requete, *args, **kwargs):
    vue = construire_vue_accueil()
    contexte = accueil(vue)
    for panneau, sujet in zip(contexte["panneaux"], vue["sujets"]):
        panneau["carte"] = en_json(carte_api.figure_carte(sujet["communes"]))
    return render(requete, "home.html", contexte)


def anomalies_view(requete, *args, **kwargs):
    return render(requete, "anomalies.html", page_anomalies(construire_vue_anomalies()))
