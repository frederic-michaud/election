"""Les instantanés simulés d'une soirée doivent être emboîtés.

C'est l'invariant sur lequel repose `deploiement/repetition_generale.sh` :
`update_scrutin_en_cours` n'importe que les communes *nouvellement* rentrées,
donc rejouer une soirée exige qu'une commune dépouillée à 5 % le soit encore à
25 %. Sans quoi la répétition sauterait des communes au lieu d'en ajouter.
"""

import json

import pytest

from scrutin.management.commands.create_fake_json_input import fabriquer
from scrutin.management.commands.update_scrutin_en_cours import communes_depouillees
from scrutin.models import Commune


def ecrire_scrutin_vide(chemin):
    """Un JSON fédéral d'avant-scrutin : toutes les communes, aucun résultat."""
    data = {"schweiz": {"abstimmtag": "20260927", "vorlagen": [{
        "vorlagenId": 6880,
        "vorlagenTitel": [{"text": "de"}, {"text": "Objet de test"}],
        "kantone": [{"gemeinden": [
            {
                "geoLevelnummer": str(numero),
                "geoLevelname": nom,
                "resultat": {
                    "jaStimmenAbsolut": None,
                    "neinStimmenAbsolut": None,
                    "anzahlStimmberechtigte": None,
                    "eingelegteStimmzettel": None,
                },
            }
            for numero, nom in Commune.objects.values_list("numero_ofs", "nom")
        ]}],
    }]}}
    chemin.write_text(json.dumps(data))
    return str(chemin)


def depouillees(chemin):
    with open(chemin) as f:
        return communes_depouillees(json.load(f)["schweiz"]["vorlagen"][0])


@pytest.mark.lent
@pytest.mark.django_db
def test_instantanes_emboites(base_demo, tmp_path):
    graine = ecrire_scrutin_vide(tmp_path / "graine.json")

    fabriquer(graine, str(tmp_path / "tot.json"), fraction=0.05)
    fabriquer(graine, str(tmp_path / "tard.json"), fraction=0.25)

    tot = depouillees(tmp_path / "tot.json")
    tard = depouillees(tmp_path / "tard.json")

    assert tot, "aucune commune dépouillée à 5 %"
    assert tot < tard, "le tour suivant doit ajouter des communes, pas en retirer"


@pytest.mark.lent
@pytest.mark.django_db
def test_la_fraction_est_a_peu_pres_respectee(base_demo, tmp_path):
    graine = ecrire_scrutin_vide(tmp_path / "graine.json")
    total = Commune.objects.count()

    fabriquer(graine, str(tmp_path / "moitie.json"), fraction=0.5)

    assert 0.4 * total < len(depouillees(tmp_path / "moitie.json")) < 0.6 * total
