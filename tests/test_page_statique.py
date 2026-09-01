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
