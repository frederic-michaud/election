"""Les instantanés simulés d'une soirée doivent être emboîtés.

`deploiement/repetition_generale.sh` rejoue une soirée : une commune
dépouillée à 5 % doit l'être encore à 25 %, comme un vrai soir. Sans quoi
l'avance de la répétition pourrait reculer d'un tour à l'autre.
"""

import json

import pytest

from scrutin.management.commands.create_fake_json_input import fabriquer
from scrutin.management.commands.update_scrutin_en_cours import communes_depouillees
from scrutin.models import Commune, ResultatCommunalHistorique, SujetVote


def scrutin_vierge(ecrire_scrutin, chemin, nb_objets=1):
    """Un JSON d'avant-scrutin : toutes les communes de la base, aucun résultat."""
    communes = dict.fromkeys(Commune.objects.values_list("numero_ofs", flat=True), False)
    return str(ecrire_scrutin(chemin, [communes] * nb_objets))


def depouillees(chemin, objet=0):
    with open(chemin) as f:
        return communes_depouillees(json.load(f)["schweiz"]["vorlagen"][objet])


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


@pytest.mark.lent
@pytest.mark.django_db
def test_les_objets_retiennent_les_memes_communes(base_demo, tmp_path, ecrire_scrutin):
    """Une commune sans historique pour un objet ne décale pas le tirage."""
    premier_sujet = SujetVote.objects.order_by("date").first()
    sans_historique = ResultatCommunalHistorique.objects.filter(
        sujet_vote=premier_sujet).order_by("commune__numero_ofs").first()
    sans_historique.delete()
    graine = scrutin_vierge(ecrire_scrutin, tmp_path / "graine.json", nb_objets=3)

    fabriquer(graine, str(tmp_path / "soiree.json"), fraction=0.25)

    objets = [depouillees(tmp_path / "soiree.json", objet) for objet in range(3)]
    ofs_retire = sans_historique.commune.numero_ofs
    assert objets[0] - {ofs_retire} == objets[1] - {ofs_retire} == objets[2] - {ofs_retire}
