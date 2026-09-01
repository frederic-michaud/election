
from django.shortcuts import render

import carte.API as api
from scrutin.donnees import construire_vue_accueil


def carte_view(requete, *args, **kwargs):
    # Le premier objet du scrutin le plus récent.
    sujet = construire_vue_accueil()["sujets"][0]
    div_containing_plot = api.generate_carte_plot(sujet["communes"])
    return render(requete, "home.html", {'plot': div_containing_plot})
