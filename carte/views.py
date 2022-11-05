
import carte.API as api
from django.shortcuts import render

def carte_view(requete, *args, **kwargs):
    div_containing_plot = api.generate_carte_plot(6)
    return render(requete, "home.html", {'plot': div_containing_plot})
