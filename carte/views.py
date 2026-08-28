
from django.shortcuts import render

import carte.API as api
from scrutin.models import SujetVote


def carte_view(requete, *args, **kwargs):
    # Le premier objet du scrutin le plus récent — l'identifiant était codé en
    # dur (6), celui de septembre 2022.
    dernier = SujetVote.objects.latest('date')
    sujet = SujetVote.objects.filter(date=dernier.date).order_by('sujet_id').first()
    div_containing_plot = api.generate_carte_plot(sujet.id)
    return render(requete, "home.html", {'plot': div_containing_plot})
