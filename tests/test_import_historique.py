"""Reconstruction de l'historique communal depuis un JSON fédéral.

Le fichier `donnee_federale_v3.txt` qui alimentait l'ACP n'existe plus. Cette
commande le remplace par la source publique, au format du jour J.
"""

import json

import pytest

from scrutin.management.commands.importer_historique import importer
from scrutin.models import Canton, Commune, District, ResultatCommunalHistorique, SujetVote

pytestmark = pytest.mark.django_db


def ecrire_json(chemin, communes, nb_objets=1):
    """`communes` : liste de (numero_ofs, nom, oui, non) ou oui=None si non dépouillée."""
    objets = []
    for i in range(nb_objets):
        objets.append({
            "vorlagenId": 6000 + i,
            "vorlagenTitel": [{"text": f"DE {i}"}, {"text": f"Objet {i}"}],
            "kantone": [{"gemeinden": [
                {
                    "geoLevelnummer": str(ofs),
                    "geoLevelname": nom,
                    "resultat": {
                        "jaStimmenAbsolut": oui,
                        "neinStimmenAbsolut": non,
                        "anzahlStimmberechtigte": 1000,
                        "eingelegteStimmzettel": None if oui is None else oui + non,
                    },
                }
                for ofs, nom, oui, non in communes
            ]}],
        })
    chemin.write_text(json.dumps({"abstimmtag": "20210613", "schweiz": {"vorlagen": objets}}))
    return str(chemin)


@pytest.fixture
def commune():
    canton = Canton.objects.create(nom="Vaud", abreviation="VD")
    district = District.objects.create(nom="Lausanne", numero_ofs=1, canton=canton)
    return Commune.objects.create(nom="Lausanne", numero_ofs=5586, district=district, canton=canton)


def test_importe_les_resultats_et_cree_les_sujets(tmp_path, commune):
    chemin = ecrire_json(tmp_path / "v.json", [(5586, "Lausanne", 400, 600)], nb_objets=2)

    nb_sujets, nb_resultats, inconnues = importer(chemin)

    assert (nb_sujets, nb_resultats, inconnues) == (2, 2, set())
    assert SujetVote.objects.count() == 2
    assert str(SujetVote.objects.first().date) == "2021-06-13"
    resultat = ResultatCommunalHistorique.objects.first()
    assert (resultat.nombre_oui, resultat.nombre_non, resultat.bulletins_rentres) == (400, 600, 1000)


def test_relancable_sans_doublon(tmp_path, commune):
    chemin = ecrire_json(tmp_path / "v.json", [(5586, "Lausanne", 400, 600)])

    importer(chemin)
    importer(chemin)

    assert ResultatCommunalHistorique.objects.count() == 1
    assert SujetVote.objects.count() == 1


def test_ignore_une_commune_absente_de_la_base(tmp_path, commune):
    chemin = ecrire_json(tmp_path / "v.json",
                         [(5586, "Lausanne", 400, 600), (9999, "Inconnue", 10, 20)])

    _, nb_resultats, inconnues = importer(chemin)

    assert nb_resultats == 1
    assert inconnues == {"Inconnue"}


def test_ignore_une_commune_non_depouillee(tmp_path, commune):
    chemin = ecrire_json(tmp_path / "v.json", [(5586, "Lausanne", None, None)])

    _, nb_resultats, _ = importer(chemin)

    assert nb_resultats == 0
    assert not ResultatCommunalHistorique.objects.exists()
