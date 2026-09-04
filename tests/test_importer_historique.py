"""Reconstruction de l'historique communal depuis le cube STAT-TAB (B4).

Le réseau est remplacé par deux fonctions monkeypatchées : les métadonnées du
cube et le tableau (géo, objet, résultat, valeur) que renvoie l'API PX-Web.
"""

import datetime

import pytest

from scrutin.management.commands import importer_historique as ih
from scrutin.models import Canton, Commune, District, ResultatCommunalHistorique, SujetVote

pytestmark = pytest.mark.django_db

OBJETS = {
    "6870": (datetime.date(2026, 6, 14), "Modification de la loi sur le service civil"),
    "6180": (datetime.date(2018, 6, 10), "Initiative « Monnaie pleine »"),
    "1930": (datetime.date(1960, 5, 29), "Arrêté sur le contrôle des prix"),
}
NOMS = {5586: "Lausanne", 5589: "Pully", 9220: "VD-CH de l'étranger"}


def cellules(geo, objet, inscrits, bulletins, oui, non):
    return [(geo, objet, "1", inscrits), (geo, objet, "2", bulletins),
            (geo, objet, "5", oui), (geo, objet, "6", non)]


@pytest.fixture
def cube(monkeypatch):
    """Un faux cube : `cube.lignes` est ce que renvoie l'API, `cube.appels` ce qu'on lui a demandé."""
    class Cube:
        lignes = []
        appels = []
    monkeypatch.setattr(ih, "lire_metadonnees", lambda: (OBJETS, NOMS))

    def lire_resultats(codes):
        Cube.appels.append(list(codes))
        return [ligne for ligne in Cube.lignes if ligne[1] in codes]
    monkeypatch.setattr(ih, "lire_resultats", lire_resultats)
    return Cube


@pytest.fixture
def lausanne():
    canton = Canton.objects.create(nom="Vaud", abreviation="VD")
    district = District.objects.create(nom="Lausanne", numero_ofs=2225, canton=canton)
    return Commune.objects.create(nom="Lausanne", numero_ofs=5586, district=district, canton=canton)


def test_cree_les_sujets_et_les_resultats_des_seules_communes(cube, lausanne):
    cube.lignes = (cellules("CH", "6870", "5669113", "3303080", "1690622", "1532160")
                   + cellules("002225", "6870", "100000", "50000", "20000", "30000")
                   + cellules("5586", "6870", "67952", "35674", "10626", "24000"))

    nb_objets, nb_resultats = ih.importer(depuis=datetime.date(2026, 1, 1), rapport=lambda _: None)

    assert (nb_objets, nb_resultats) == (1, 1)
    sujet = SujetVote.objects.get()
    assert (sujet.sujet_id, str(sujet.date)) == (6870, "2026-06-14")
    assert sujet.nom == "Modification de la loi sur le service civil"
    resultat = ResultatCommunalHistorique.objects.get()
    assert resultat.commune == lausanne
    assert (resultat.electeurs_inscrits, resultat.bulletins_rentres,
            resultat.nombre_oui, resultat.nombre_non) == (67952, 35674, 10626, 24000)


def test_une_valeur_manquante_ne_donne_pas_de_resultat(cube, lausanne):
    cube.lignes = cellules("5586", "6870", "67952", "...", "10626", "24000")

    _, nb_resultats = ih.importer(depuis=datetime.date(2026, 1, 1), rapport=lambda _: None)

    assert nb_resultats == 0
    assert not ResultatCommunalHistorique.objects.exists()


def test_une_commune_absente_de_la_base_est_signalee(cube, lausanne, caplog):
    cube.lignes = (cellules("5586", "6870", "1", "1", "1", "1")
                   + cellules("5589", "6870", "1", "1", "1", "1"))

    _, nb_resultats = ih.importer(depuis=datetime.date(2026, 1, 1), rapport=lambda _: None)

    assert nb_resultats == 1
    assert "[5589]" in caplog.text


def test_cree_les_pseudo_communes_de_l_etranger(cube, lausanne):
    cube.lignes = cellules("9220", "6870", "20000", "5000", "3000", "2000")

    _, nb_resultats = ih.importer(depuis=datetime.date(2026, 1, 1), rapport=lambda _: None)

    assert nb_resultats == 1
    etranger = Commune.objects.get(numero_ofs=9220)
    assert etranger.nom == "VD-CH de l'étranger"
    assert etranger.canton.abreviation == "VD"
    assert etranger.district.numero_ofs == 9220


def test_relancable_sans_doublon_et_avec_mise_a_jour(cube, lausanne):
    cube.lignes = cellules("5586", "6870", "1", "1", "10", "20")
    ih.importer(depuis=datetime.date(2026, 1, 1), rapport=lambda _: None)
    cube.lignes = cellules("5586", "6870", "1", "1", "11", "20")

    ih.importer(depuis=datetime.date(2026, 1, 1), rapport=lambda _: None)

    assert SujetVote.objects.count() == 1
    assert ResultatCommunalHistorique.objects.get().nombre_oui == 11


def test_depuis_filtre_les_objets_et_lot_decoupe_les_appels(cube, lausanne):
    cube.lignes = []

    nb_objets, _ = ih.importer(depuis=datetime.date(2018, 1, 1), lot=1, rapport=lambda _: None)

    assert nb_objets == 2
    assert cube.appels == [["6180"], ["6870"]]
    assert list(SujetVote.objects.order_by("date").values_list("sujet_id", flat=True)) == [6180, 6870]


def test_resserrer_la_fenetre_purge_l_historique_plus_ancien(cube, lausanne):
    cube.lignes = cellules("5586", "6180", "1", "1", "1", "1") + cellules("5586", "6870", "1", "1", "1", "1")
    ih.importer(depuis=datetime.date(2018, 1, 1), rapport=lambda _: None)
    assert ResultatCommunalHistorique.objects.count() == 2

    ih.importer(depuis=datetime.date(2026, 1, 1), rapport=lambda _: None)

    assert list(ResultatCommunalHistorique.objects.values_list("sujet_vote__sujet_id", flat=True)) == [6870]
    assert list(SujetVote.objects.values_list("sujet_id", flat=True)) == [6870]
