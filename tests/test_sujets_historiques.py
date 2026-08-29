"""Le nombre d'objets historiques doit se déduire des données, pas être en dur.

Avec le « 55 » codé en dur, ajouter une votation à l'historique écartait
*toutes* les communes de l'ACP — silencieusement, puisque l'avertissement
n'était pas émis. C'est le piège le plus coûteux du dépôt : il ne se serait
manifesté qu'un dimanche de scrutin.
"""

import datetime

import pytest

from scrutin.models import (
    Canton,
    Commune,
    District,
    ResultatCommunalHistorique,
    ScrutinAPI,
    SujetVote,
    nb_sujets_historiques,
)


def peupler(nb_sujets, nb_communes=3):
    canton = Canton.objects.create(nom="Vaud", abreviation="VD")
    district = District.objects.create(nom="Lavaux-Oron", numero_ofs=1, canton=canton)
    communes = [
        Commune.objects.create(nom=f"Commune {i}", numero_ofs=1000 + i,
                               canton=canton, district=district)
        for i in range(nb_communes)
    ]
    for i in range(nb_sujets):
        ajouter_sujet(communes, i)
    return communes


def ajouter_sujet(communes, index):
    sujet = SujetVote.objects.create(
        nom=f"Objet {index}", sujet_id=index + 1,
        date=datetime.date(2020, 1, 1) + datetime.timedelta(days=91 * index),
    )
    for rang, commune in enumerate(communes):
        ResultatCommunalHistorique.objects.create(
            commune=commune, sujet_vote=sujet,
            nombre_oui=400 + rang, nombre_non=600 - rang,
            electeurs_inscrits=2000, bulletins_rentres=1000,
        )
    return sujet


@pytest.mark.django_db
def test_le_nombre_de_sujets_historiques_se_deduit_des_voix():
    communes = peupler(nb_sujets=4)
    assert nb_sujets_historiques() == 4

    # Un objet du jour J n'a pas encore de ResultatCommunalHistorique : il ne compte pas.
    SujetVote.objects.create(nom="Jour J", sujet_id=99,
                             date=datetime.date(2026, 9, 27))
    assert nb_sujets_historiques() == 4

    ajouter_sujet(communes, index=4)
    assert nb_sujets_historiques() == 5


@pytest.mark.django_db
def test_ajouter_une_votation_n_ecarte_pas_les_communes_de_l_acp():
    communes = peupler(nb_sujets=4)
    (sujets, retenues), matrice = ScrutinAPI.getVotationMatrixWithMetaInfo()
    assert len(retenues) == len(communes)
    assert len(sujets) == 4

    ajouter_sujet(communes, index=4)

    (sujets, retenues), matrice = ScrutinAPI.getVotationMatrixWithMetaInfo()
    assert len(retenues) == len(communes)
    assert len(sujets) == 5
    assert all(len(ligne) == 5 for ligne in matrice)


@pytest.mark.django_db
def test_une_commune_a_l_historique_incomplet_est_ecartee_avec_un_avertissement():
    communes = peupler(nb_sujets=4)
    ResultatCommunalHistorique.objects.filter(commune=communes[0]).first().delete()

    with pytest.warns(UserWarning, match="Commune 0"):
        (_, retenues), _ = ScrutinAPI.getVotationMatrixWithMetaInfo()

    assert communes[0] not in retenues
    assert len(retenues) == len(communes) - 1
