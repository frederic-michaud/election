from django.shortcuts import render

from pca.donnees import NB_COMPOSANTES, nuage_communes, nuage_objets
from pca.figures import figure_nuage
from scrutin import charte
from scrutin.graphiques import en_json

AXES = [f"Axe {numero}" for numero in range(1, NB_COMPOSANTES + 1)]


def _contexte(figure, unite, exemple, forme=""):
    return {
        "nuage": en_json(figure),
        "axes": AXES,
        "unite": unite,
        "exemple": exemple,
        "forme": forme,
        "config": charte.CONFIG_NUAGE,
    }


def nuage_communes_view(requete, *args, **kwargs):
    return render(requete, "nuage_communes.html",
                  _contexte(figure_nuage(nuage_communes()), "communes", "Lau"))


def nuage_objets_view(requete, *args, **kwargs):
    return render(requete, "nuage_objets.html",
                  _contexte(figure_nuage(nuage_objets(), objets=True), "objets", "AVS", "carre"))
