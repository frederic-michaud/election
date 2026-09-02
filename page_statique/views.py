from django.shortcuts import get_object_or_404, render

from page_statique.models import PageStatique


def static_view(requete, url):
    page = get_object_or_404(PageStatique, url=url)
    return render(requete, "static.html", {"page_content": page})
