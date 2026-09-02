"""Archivage du jour J dans l'historique.

Le piège : `run_extrapolation` écrit ses estimations dans les lignes des
communes non dépouillées. Les archiver nourrirait l'ACP de chiffres inventés.
"""

import datetime

import pytest

from scrutin.management.commands.archiver_scrutin import archiver
from scrutin.models import (
    Canton,
    Commune,
    District,
    ResultatCommunalEnCours,
    ResultatCommunalHistorique,
    SujetVote,
)

pytestmark = pytest.mark.django_db

JOUR = datetime.date(2026, 9, 27)


@pytest.fixture
def scrutin():
    canton = Canton.objects.create(nom="Vaud", abreviation="VD")
    district = District.objects.create(nom="Lausanne", numero_ofs=1, canton=canton)
    sujet = SujetVote.objects.create(nom="Objet", sujet_id=7000, date=JOUR)
    for ofs, comptabilise in [(5586, True), (5587, False)]:
        commune = Commune.objects.create(nom=f"C{ofs}", numero_ofs=ofs,
                                         district=district, canton=canton)
        ResultatCommunalEnCours.objects.create(
            commune=commune, sujet_vote=sujet, nombre_oui=400, nombre_non=600,
            electeurs_inscrits=1500, bulletins_rentres=1000,
            electeur_election_precedente=1500, comptabilise=comptabilise)
    return sujet


def test_n_archive_que_les_communes_depouillees(scrutin):
    archives, ignores = archiver(JOUR)

    assert (archives, ignores) == (1, 1)
    assert [r.commune.numero_ofs for r in ResultatCommunalHistorique.objects.all()] == [5586]


def test_relancable_sans_doublon(scrutin):
    archiver(JOUR)
    archiver(JOUR)

    assert ResultatCommunalHistorique.objects.count() == 1


def test_ne_touche_pas_aux_autres_scrutins(scrutin):
    autre = SujetVote.objects.create(nom="Vieux", sujet_id=6000,
                                     date=datetime.date(2020, 1, 1))
    ResultatCommunalHistorique.objects.create(
        commune=Commune.objects.first(), sujet_vote=autre, nombre_oui=1,
        nombre_non=2, electeurs_inscrits=3, bulletins_rentres=3)

    archiver(JOUR)

    assert ResultatCommunalHistorique.objects.get(sujet_vote=autre).nombre_oui == 1
