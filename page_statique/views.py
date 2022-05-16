from django.shortcuts import render
from page_statique.models import PageStatique

# a useless comment here.
def static_view(requete, *args, **kwargs):
    pages = PageStatique.objects.filter(url = requete.path[1:])
    if len(pages) == 1:
        page = pages[0]
    else:
        raise Exception(requete.path)

    return render(requete, "static.html", {"page_content" : page})