"""Les instantanés simulés d'une soirée doivent être emboîtés.

`deploiement/repetition_generale.sh` rejoue une soirée : une commune
dépouillée à 5 % doit l'être encore à 25 %, comme un vrai soir. Sans quoi
l'avance de la répétition pourrait reculer d'un tour à l'autre.
"""

import json

import pytest

from scrutin.management.commands.create_fake_json_input import fabriquer
from scrutin.management.commands.update_scrutin_en_cours import communes_depouillees
from scrutin.models import Commune


def scrutin_vierge(ecrire_scrutin, chemin):
    """Un JSON d'avant-scrutin : toutes les communes de la base, aucun résultat."""
    communes = dict.fromkeys(Commune.objects.values_list("numero_ofs", flat=True), False)
    return str(ecrire_scrutin(chemin, [communes]))


def depouillees(chemin):
    with open(chemin) as f:
        return communes_depouillees(json.load(f)["schweiz"]["vorlagen"][0])


@pytest.mark.lent
@pytest.mark.django_db
def test_instantanes_emboites(base_demo, tmp_path, ecrire_scrutin):
    graine = scrutin_vierge(ecrire_scrutin, tmp_path / "graine.json")

    fabriquer(graine, str(tmp_path / "tot.json"), fraction=0.05)
    fabriquer(graine, str(tmp_path / "tard.json"), fraction=0.25)

    tot = depouillees(tmp_path / "tot.json")
    tard = depouillees(tmp_path / "tard.json")

    assert tot, "aucune commune dépouillée à 5 %"
    assert tot < tard, "le tour suivant doit ajouter des communes, pas en retirer"


@pytest.mark.lent
@pytest.mark.django_db
def test_la_fraction_est_a_peu_pres_respectee(base_demo, tmp_path, ecrire_scrutin):
    graine = scrutin_vierge(ecrire_scrutin, tmp_path / "graine.json")
    total = Commune.objects.count()

    fabriquer(graine, str(tmp_path / "moitie.json"), fraction=0.5)

    assert 0.4 * total < len(depouillees(tmp_path / "moitie.json")) < 0.6 * total
