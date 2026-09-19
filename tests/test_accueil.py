"""La page d'accueil : mise en forme, carte, et la page sur la base fictive."""

import json
import re

import plotly.graph_objects as go
import pytest
from plotly.offline import get_plotlyjs_version

from carte.API import figure_carte
from scrutin.graphiques import barre, en_json, panneau, pourcentage


def test_pourcentage_a_la_francaise():
    assert pourcentage(0.46887) == "46,9\u00a0%"
    assert pourcentage(1) == "100,0\u00a0%"


def test_le_depouille_dans_l_intervalle_n_est_pas_dessine():
    forme = barre(oui_connu=0.49, oui_extrapole=0.47, marge=3)
    assert forme["depouille"] is None
    assert (forme["bas"], forme["largeur"]) == ("44.00", "6.00")


def test_le_depouille_hors_de_l_intervalle_pointe_vers_son_bord():
    monte = barre(oui_connu=0.30, oui_extrapole=0.43, marge=3)["depouille"]
    assert monte["sens"] == "droite"
    assert (monte["position"], monte["fleche"]) == ("30.00", "40.00")
    assert (monte["trajet_debut"], monte["trajet_largeur"]) == ("30.00", "10.00")
    descend = barre(oui_connu=0.544, oui_extrapole=0.469, marge=3)["depouille"]
    assert descend["sens"] == "gauche"
    assert descend["fleche"] == "49.90"


def test_l_intervalle_est_rogne_a_0_et_100():
    forme = barre(oui_connu=0.99, oui_extrapole=0.99, marge=3)
    assert float(forme["bas"]) + float(forme["largeur"]) == 100


def test_le_panneau_d_un_objet():
    p = panneau({"nom": "Loi", "oui_connu": 0.544, "oui_extrapole": 0.5})
    assert p["verdict"] == "oui"
    assert (p["extrapole"], p["connu"]) == ("50,0\u00a0%", "54,4\u00a0%")
    assert p["bornes"] == "47,5\u00a0–\u00a052,5\u00a0%"


def test_le_json_d_une_figure_ne_peut_pas_refermer_sa_balise():
    figure = go.Figure(layout={"title": {"text": "</script><b>&</b>"}})
    texte = en_json(figure)
    assert "<" not in texte and ">" not in texte and "&" not in texte
    assert json.loads(texte)["layout"]["title"]["text"] == "</script><b>&</b>"


def test_la_carte_est_zoomable_et_cadree_sur_le_pays():
    figure = figure_carte({1: {"oui": 0.6, "comptabilise": True}})
    assert figure.data[0].type == "choroplethmap"
    (x0, y0), (x1, y1) = figure.layout.meta["emprise"]
    assert 5.9 < x0 < 6 and 10.4 < x1 < 10.6 and 45.8 < y0 < 45.9 and 47.7 < y1 < 47.9
    assert figure.layout.map.style["sources"] == {}
    bornes = figure.layout.map.bounds
    assert bornes.west < x0 and bornes.east > x1 and bornes.south < y0 and bornes.north > y1
    axe = figure.layout.coloraxis
    assert (axe.cmin, axe.cmid, axe.cmax, axe.showscale) == (32, 50, 68, False)


@pytest.mark.lent
@pytest.mark.django_db
def test_la_page_d_accueil(base_demo, client):
    html = client.get("/").content.decode()
    assert html.count('<article class="panneau">') == 3
    assert html.count('<script type="application/json">') == 3
    assert '"type":"choroplethmap"' in html
    assert "tracerCartes();" in html
    assert f"https://cdn.plot.ly/plotly-{get_plotlyjs_version()}.min.js" in html
    assert re.search(r"Votations fédérales <span class=\"quand\">du \d{1,2} [a-zéû]+ \d{4}</span>", html)
    assert re.search(r"Dépouillement en cours · \d\d:\d\d", html)
    assert '<a href="/" aria-current="page">Accueil</a>' in html
    # Les deux pages de lecture de l'ACP, dans le menu du pied de page.
    for lien in ('/nuage-acp', '/objets-acp'):
        assert f'href="{lien}"' in html
    assert 'href="/cartes"' not in html
    assert "Déja dépouillés" not in html
