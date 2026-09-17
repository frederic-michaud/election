"""Les instantanés simulés d'une soirée doivent être emboîtés.

C'est l'invariant sur lequel repose `deploiement/repetition_generale.sh` :
`update_scrutin_en_cours` n'importe que les communes *nouvellement* rentrées,
donc rejouer une soirée exige qu'une commune dépouillée à 5 % le soit encore à
25 %. Sans quoi la répétition sauterait des communes au lieu d'en ajouter.
"""

import json

import pytest

from scrutin.management.commands.create_fake_json_input import fabriquer
from scrutin.management.commands.update_scrutin_en_cours import (
    communes_depouillees,
    get_new_commune,
)
from scrutin.models import Commune, ResultatCommunalHistorique, SujetVote


def scrutin_vierge(ecrire_scrutin, chemin, nb_objets=1):
    """Un JSON d'avant-scrutin : toutes les communes de la base, aucun résultat."""
    communes = dict.fromkeys(Commune.objects.values_list("numero_ofs", flat=True), False)
    return str(ecrire_scrutin(chemin, [communes] * nb_objets))


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


@pytest.mark.lent
@pytest.mark.django_db
def test_les_objets_retiennent_les_memes_communes(base_demo, tmp_path, ecrire_scrutin):
    """Le tirage doit être propre à la commune, pas séquentiel.

    `update_scrutin_en_cours` n'importe une commune que lorsqu'elle est rentrée
    pour *tous* les objets. Avec un tirage séquentiel, une commune privée
    d'historique sur un seul objet décalait la suite du tirage et les objets ne
    retenaient plus les mêmes communes : l'intersection tombait de 110 à 7,
    soit le garde-fou de `get_extrapolation`, et la répétition n'affichait plus
    aucune projection.
    """
    sujets = SujetVote.objects.order_by("date")
    premiere = Commune.objects.get(numero_ofs=Commune.objects.values_list(
        "numero_ofs", flat=True)[0])
    ResultatCommunalHistorique.objects.filter(
        sujet_vote=sujets[1], commune=premiere).delete()

    graine = scrutin_vierge(ecrire_scrutin, tmp_path / "graine.json", nb_objets=3)
    fabriquer(graine, str(tmp_path / "tour.json"), fraction=0.05)

    with open(tmp_path / "tour.json") as f:
        objets = json.load(f)["schweiz"]["vorlagen"]
    par_objet = [communes_depouillees(objet) for objet in objets]

    assert len(set(map(frozenset, par_objet))) == 1, "les objets divergent"
    assert get_new_commune(graine, str(tmp_path / "tour.json")) == par_objet[0]
