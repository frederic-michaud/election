from django.shortcuts import render

import carte.API as api
from scrutin import charte
from scrutin.donnees import construire_vue_accueil
from scrutin.graphiques import en_json


def carte_view(requete, *args, **kwargs):
    # Le premier objet du scrutin le plus récent, sur la carte de l'accueil.
    sujet = construire_vue_accueil()["sujets"][0]
    return render(requete, "carte.html", {
        "nom": sujet["nom"],
        "carte": en_json(api.figure_carte(sujet["communes"])),
        "config_carte": charte.CONFIG_CARTE,
    })
