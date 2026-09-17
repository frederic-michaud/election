from django.shortcuts import render

import carte.API as api
from pca.donnees import profils_par_commune
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


def carte_acp_view(requete, *args, **kwargs):
    figure = api.figure_carte_acp(profils_par_commune())
    return render(requete, "carte_acp.html", {
        "carte": en_json(figure),
        "axes": [axe["nom"] for axe in figure.layout.meta["axes"]],
        "config_carte": charte.CONFIG_CARTE,
    })
