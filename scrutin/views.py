import datetime

from django.shortcuts import render

import carte.API as carte_api
from scrutin.donnees import construire_vue_accueil
from scrutin.graphiques import histogramme


def home_view(requete, *args, **kwargs):
    vue = construire_vue_accueil()
    date = datetime.date.fromisoformat(vue["date"]).strftime("%d %b %Y")
    return render(requete, "home.html", {
        "histo": histogramme(vue),
        "maps": [carte_api.generate_carte_plot(sujet["communes"]) for sujet in vue["sujets"]],
        "avance": f"{100*vue['avance']:.1f}%",
        "date": date,
    })
