from django.shortcuts import render

from scrutin.donnees import construire_vue_accueil
from scrutin.graphiques import accueil


def home_view(requete, *args, **kwargs):
    return render(requete, "home.html", accueil(construire_vue_accueil()))
