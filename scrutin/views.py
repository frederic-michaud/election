from django.shortcuts import render

import carte.API as carte_api
from scrutin.donnees import construire_vue_accueil
from scrutin.graphiques import accueil, en_json


def home_view(requete, *args, **kwargs):
    vue = construire_vue_accueil()
    contexte = accueil(vue)
    for panneau, sujet in zip(contexte["panneaux"], vue["sujets"]):
        panneau["carte"] = en_json(carte_api.figure_carte(sujet["communes"]))
    return render(requete, "home.html", contexte)
