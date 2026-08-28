"""Test d'intégration du pipeline sur la base fictive.

Enchaîne ``peupler_demo`` → ACP (la vraie, scikit-learn) → extrapolation, et
vérifie que la projection est cohérente. Contrairement aux tests unitaires de
``test_extrapolation.py``, on ne connaît pas ici le résultat analytiquement :
ce qu'on vérifie, c'est que la méthode **corrige effectivement le biais** du
dépouillement partiel.

Ces tests peuplent la base complète (~2 100 communes) : ils prennent quelques
secondes et portent la marque ``lent``.
"""

import warnings

import pytest
from django.core.management import call_command

from pca.models import PCAResult
from scrutin.extrapolation import get_extrapolation
from scrutin.models import Commune, ScrutinAPI, ScrutinEnCours, SujetVote

NB_VOTATIONS_HISTORIQUES = 55


@pytest.fixture(scope="module")
def base_demo(django_db_setup, django_db_blocker):
    """Peuple la base de démonstration une seule fois pour tout le module."""
    with django_db_blocker.unblock():
        call_command("peupler_demo", verbosity=0)
        yield


def sujets_du_jour():
    jour = SujetVote.objects.order_by("-date").first().date
    return list(SujetVote.objects.filter(date=jour).order_by("sujet_id"))


def resultat_reel(sujet):
    """Le résultat qu'on obtiendrait si toutes les communes étaient rentrées.

    ``peupler_demo`` écrit les vraies valeurs dans *toutes* les lignes, y
    compris celles marquées non dépouillées — c'est ce qui donne un étalon.
    """
    lignes = ScrutinEnCours.objects.filter(sujet_vote=sujet)
    oui = sum(ligne.nombre_oui for ligne in lignes)
    non = sum(ligne.nombre_non for ligne in lignes)
    return oui / (oui + non)


@pytest.mark.lent
@pytest.mark.django_db
def test_peupler_demo_produit_une_base_coherente(base_demo):
    assert Commune.objects.count() > 2000
    assert SujetVote.objects.count() == NB_VOTATIONS_HISTORIQUES + len(sujets_du_jour())
    assert PCAResult.objects.count() == Commune.objects.count()

    # Une soirée en cours : ni rien ni tout n'est dépouillé.
    lignes = ScrutinEnCours.objects.filter(sujet_vote=sujets_du_jour()[0])
    comptees = lignes.filter(comptabilise=True).count()
    assert 0 < comptees < lignes.count()


@pytest.mark.lent
@pytest.mark.django_db
def test_aucune_commune_n_est_ecartee_de_la_matrice_acp(base_demo):
    """Garde-fou sur le « 55 » codé en dur dans ``ScrutinAPI`` (piège connu).

    Une commune qui n'a pas *exactement* 55 ``Voix`` est silencieusement
    écartée de l'ACP. Le jour où l'on ajoutera une votation historique sans
    toucher à cette constante, toutes les communes disparaîtront — et ce test
    est le seul endroit qui s'en apercevra.
    """
    (sujets, communes), matrice = ScrutinAPI.getVotationMatrixWithMetaInfo()

    assert len(communes) == Commune.objects.count()
    assert len(sujets) == NB_VOTATIONS_HISTORIQUES
    assert len(matrice) == len(communes)
    assert all(len(ligne) == NB_VOTATIONS_HISTORIQUES for ligne in matrice)


@pytest.mark.lent
@pytest.mark.django_db
def test_l_extrapolation_corrige_le_biais_du_depouillement_partiel(base_demo):
    """Le pipeline complet : ACP réelle, puis projection.

    Les petites communes dépouillent en premier, donc le résultat brut est
    franchement faux. La projection doit être nettement meilleure — c'est la
    raison d'être du site.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        call_command("runscript", "populate_pca")

    assert PCAResult.objects.count() == Commune.objects.count()

    for sujet in sujets_du_jour():
        vrai = resultat_reel(sujet)
        connu, extrapolation, avance, sans_resultat, _, _ = get_extrapolation(sujet)

        erreur_brute = abs(connu - vrai)
        erreur_projetee = abs(extrapolation - vrai)

        assert erreur_projetee < 0.05, f"projection trop loin du réel pour {sujet}"
        # Marge large : mesuré autour d'un facteur 10 sur la base de démo.
        assert erreur_projetee < erreur_brute / 3, (
            f"la projection n'améliore pas le résultat brut pour {sujet} "
            f"(brut {erreur_brute:.4f}, projeté {erreur_projetee:.4f})"
        )
        # L'avance est une part de bulletins, pas de communes : avec plus de la
        # moitié des communes rentrées mais les plus petites, elle reste faible.
        assert 0 < avance < 1
        assert len(sans_resultat) > 0
