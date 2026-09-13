"""Ce que la page d'accueil met en forme, sans base de données.

`scrutin.graphiques` ne consomme que le contrat de vue : ses fonctions de
formatage et de géométrie se testent donc sur un dict écrit à la main.
"""

from scrutin.graphiques import MARGE_FOURCHETTE, _barre, date_longue, panneaux, pourcent


def test_les_pourcentages_sont_en_francais():
    # Virgule décimale et espace insécable : le site parle français, même si
    # `settings.py` est encore en `en-us`.
    assert pourcent(0.469) == "46,9 %"
    assert pourcent(0.5, decimales=0) == "50 %"


def test_la_date_est_en_toutes_lettres():
    assert date_longue("2026-09-27") == "27 septembre 2026"


def test_la_geometrie_de_la_barre_sort_a_point_decimal():
    # Rendues comme des flottants, ces valeurs deviendraient « 46,9 » sous une
    # locale française et la règle CSS serait ignorée.
    barre = _barre(0.544, 0.469, 2.5)
    for cle in ("moustache_gauche", "moustache_largeur", "connu", "cible"):
        assert "," not in barre[cle]
        assert float(barre[cle]) >= 0


def test_le_depouille_ne_se_dessine_que_hors_de_l_intervalle():
    # Dedans : la flèche ne dirait rien.
    assert not _barre(0.470, 0.469, 2.5)["montrer_connu"]
    # Dehors : on montre d'où l'extrapolation corrige.
    dehors = _barre(0.544, 0.469, 2.5)
    assert dehors["montrer_connu"]
    assert dehors["sens"] == "gauche"  # l'extrapolé est sous le dépouillé


def test_un_panneau_par_objet_avec_son_verdict_et_sa_fourchette():
    vue = {
        "date": "2026-09-27",
        "avance": 0.157,
        "sujets": [
            {"id": 1, "nom": "Objet accepté", "oui_connu": 0.52, "oui_extrapole": 0.544,
             "communes": {}},
            {"id": 2, "nom": "Objet refusé", "oui_connu": 0.40, "oui_extrapole": 0.419,
             "communes": {}},
        ],
    }
    accepte, refuse = panneaux(vue)
    assert accepte["verdict"] == "oui"
    assert refuse["verdict"] == "non"
    assert accepte["extrapole"] == "54,4 %"
    # La fourchette est la constante provisoire, pas une valeur du contrat.
    assert accepte["bornes"] == "51,9 – 56,9 %"
    assert MARGE_FOURCHETTE == 2.5
    # Le verdict n'est porté que par la couleur : l'aria-label le rattrape.
    assert "Extrapolé 54,4" in accepte["resume"]
