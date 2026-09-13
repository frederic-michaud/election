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


def test_le_menu_affiche_un_onglet_par_page(client):
    PageStatique.objects.create(titre="Méthodes", contenu="", url="methode", ordre=1)
    html = client.get("/methode").content.decode()
    # Le menu est en pied de page depuis la variante D′, et la page servie s'y
    # signale : c'est la seule marque de la page courante, la couleur seule ne
    # suffirait pas.
    assert '<a href="/methode" aria-current="page">Méthodes</a>' in html
    # « Cartes » a été retiré du menu par la maquette : la carte est sur
    # l'accueil, un panneau par objet. La route, elle, existe toujours.
    assert ">Cartes</a>" not in html
    assert 'href="NA"' not in html


def test_une_autre_page_n_est_pas_marquee_comme_courante(client):
    PageStatique.objects.create(titre="Contact", contenu="", url="contact", ordre=2)
    html = client.get("/contact").content.decode()
    assert '<a href="/">Accueil</a>' in html
    assert '<a href="/contact" aria-current="page">Contact</a>' in html
