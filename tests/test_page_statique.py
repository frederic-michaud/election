"""La route attrape-tout des pages éditables renvoie un 404 propre.

Elle levait une ``Exception`` brute (donc un 500) pour toute URL inconnue,
y compris un simple favicon demandé par le navigateur.
"""

import pytest

from page_statique.models import PageStatique

pytestmark = pytest.mark.django_db


def test_une_page_existante_est_servie(client):
    PageStatique.objects.create(titre="Méthodes", contenu="<p>ACP</p>", url="methodes")
    reponse = client.get("/methodes")
    assert reponse.status_code == 200
    assert "ACP" in reponse.content.decode()


@pytest.mark.parametrize("url", ["/inconnue", "/favicon.ico", "/a/b", "/methodes/"])
def test_une_url_inconnue_renvoie_404(client, url):
    assert client.get(url).status_code == 404


def test_le_menu_expose_les_pages_triees(client):
    PageStatique.objects.create(titre="Contact", contenu="", url="contact", ordre=2)
    PageStatique.objects.create(titre="Méthodes", contenu="", url="methode", ordre=1)
    contexte = client.get("/contact").context["pages_statiques"]
    assert [page.url for page in contexte] == ["methode", "contact"]
