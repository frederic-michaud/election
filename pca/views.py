from django.shortcuts import render

from carte.API import figure_carte_acp
from pca.donnees import nuage_communes, nuage_objets, profils_par_commune
from pca.figures import figure_nuage
from scrutin import charte
from scrutin.graphiques import en_json


def _pourcent(part):
    return f"{part:.1%}".replace(".", ",").replace("%", " %")


def _contexte(donnees, objets):
    """Le nuage et, à côté, les deux cartes qui suivent ses menus d'axes."""
    return {
        "nuage": en_json(figure_nuage(donnees, objets)),
        "axes": [{"nom": f"Axe {numero}", "variance": _pourcent(part)}
                 for numero, part in enumerate(donnees["variance"], start=1)],
        "periode": donnees["periode"],
        "unite": "objets" if objets else "communes",
        "exemple": "AVS" if objets else "Lau",
        "forme": "carre" if objets else "",
        "config": charte.CONFIG_NUAGE,
        "carte": en_json(figure_carte_acp(profils_par_commune())),
        "config_carte": charte.CONFIG_CARTE,
    }


def nuage_communes_view(requete, *args, **kwargs):
    return render(requete, "nuage_communes.html", _contexte(nuage_communes(), objets=False))


def nuage_objets_view(requete, *args, **kwargs):
    return render(requete, "nuage_objets.html", _contexte(nuage_objets(), objets=True))
