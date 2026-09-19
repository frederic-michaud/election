"""La page Contact : semée depuis le dépôt, et son formulaire qui envoie un courriel.

La page doit rester cachable (ni jeton CSRF, ni cookie) : le formulaire poste
vers une vue à part, la seule requête POST du site.
"""

import pytest
from django.core import mail
from django.test import Client

from page_statique.models import PageStatique
from page_statique.pages import PAGES, peupler_pages

pytestmark = pytest.mark.django_db

VALIDE = {"nom": "Anne Exemple", "courriel": "anne@example.org", "message": "Bravo pour le site"}


@pytest.fixture
def client_strict():
    """Le client de test ignore le CSRF par défaut ; le vrai navigateur, non."""
    return Client(enforce_csrf_checks=True)


def test_peupler_pages_aligne_la_base_sur_le_depot():
    PageStatique.objects.create(titre="Méthodes", contenu="<p>ancienne</p>", url="methode")
    assert peupler_pages() == ["methode"]
    assert sorted(PageStatique.objects.values_list("url", flat=True)) == sorted(u for u, _, _ in PAGES)
    peupler_pages()  # idempotent
    assert PageStatique.objects.count() == len(PAGES)


def test_la_page_contact_reste_cachable(client):
    peupler_pages()
    reponse = client.get("/contact")
    html = reponse.content.decode()
    assert reponse.status_code == 200
    assert 'action="/contact/envoyer"' in html
    assert "csrfmiddlewaretoken" not in html
    assert not reponse.cookies


def test_un_message_part_avec_l_adresse_du_visiteur_en_reponse(client_strict, settings):
    settings.CONTACT_DESTINATAIRE = "nous@example.org"
    reponse = client_strict.post("/contact/envoyer", VALIDE)
    assert reponse.status_code == 200
    assert "Merci" in reponse.content.decode()
    [courriel] = mail.outbox
    assert courriel.to == ["nous@example.org"]
    assert courriel.reply_to == ["anne@example.org"]
    assert courriel.subject == "[Politiques.ch] Message de Anne Exemple"
    assert "Bravo pour le site" in courriel.body


def test_un_nom_sur_plusieurs_lignes_ne_casse_pas_l_objet(client_strict, settings):
    settings.CONTACT_DESTINATAIRE = "nous@example.org"
    client_strict.post("/contact/envoyer", {**VALIDE, "nom": "Anne\r\nBcc: tous@example.org"})
    assert mail.outbox[0].subject == "[Politiques.ch] Message de Anne Bcc: tous@example.org"
    assert mail.outbox[0].bcc == []


def test_le_pot_de_miel_fait_semblant(client_strict, settings):
    settings.CONTACT_DESTINATAIRE = "nous@example.org"
    reponse = client_strict.post("/contact/envoyer", {**VALIDE, "site_web": "http://spam"})
    assert reponse.status_code == 200
    assert mail.outbox == []


@pytest.mark.parametrize("manque", [{"courriel": ""}, {"courriel": "pas-une-adresse"}, {"message": "  "}])
def test_un_message_incomplet_est_refuse(client_strict, settings, manque):
    settings.CONTACT_DESTINATAIRE = "nous@example.org"
    reponse = client_strict.post("/contact/envoyer", {**VALIDE, **manque})
    assert reponse.status_code == 400
    assert mail.outbox == []


def test_sans_destinataire_le_formulaire_le_dit(client_strict, settings):
    settings.CONTACT_DESTINATAIRE = ""
    reponse = client_strict.post("/contact/envoyer", VALIDE)
    assert reponse.status_code == 503
    assert "pas encore relié" in reponse.content.decode()
    assert mail.outbox == []


def test_la_route_n_accepte_que_post(client):
    assert client.get("/contact/envoyer").status_code == 405
