"""Tests du cœur mathématique : ``scrutin/extrapolation.py``.

Le principe de ces tests : sur des données synthétiques *exactement* linéaires,
la méthode doit retrouver les coefficients qui les ont engendrées. C'est le seul
endroit du dépôt où le résultat attendu est connu analytiquement — d'où la
valeur de ces tests par rapport à un contrôle « ça ne plante pas ».

Aucun accès réseau, aucune donnée réelle.
"""

import datetime

import numpy as np
import pytest

from pca.models import PCAResult
from scrutin.extrapolation import (
    Delta,
    Delta_fast,
    get_extrapolated_value,
    get_extrapolation,
    get_linear_parameter,
    get_percentage,
    nb_component,
)
from scrutin.models import Canton, Commune, District, ScrutinEnCours, SujetVote

# Le modèle qui engendre les données synthétiques : le % de oui et la
# participation sont des fonctions affines de la première composante ACP.
OUI_ORDONNEE, OUI_PENTE = 0.50, 0.10
PART_ORDONNEE, PART_PENTE = 0.42, 0.05


def composante(c1):
    """Une coordonnée ACP dont seul le premier axe porte de l'information."""
    return [c1, 0.0, 0.0, 0.0, 0.0, 0.0]


# --------------------------------------------------------------------------- #
# La régression, sans base de données
# --------------------------------------------------------------------------- #


def test_get_percentage_combine_composantes_et_ordonnee():
    params = np.array([1.0, 2.0, 0.0, 0.0, 0.0, 0.0, 0.25])
    assert get_percentage(np.array([0.5, 1.0, 0, 0, 0, 0]), params) == pytest.approx(2.75)


def test_delta_fast_est_equivalent_a_delta():
    """``Delta_fast`` est la version vectorisée réellement utilisée par le fit.

    ``Delta`` en est la version lisible : les deux doivent coïncider, sinon on
    optimise autre chose que ce que le code documente.
    """
    params = np.array([0.3, -0.2, 0.1, 0.0, 0.0, 0.0, 0.5])
    components = [composante(c) for c in (-1.0, -0.4, 0.2, 0.9)]
    observed = [0.31, 0.44, 0.57, 0.62]
    nb_votants = [100, 2500, 700, 40]

    assert Delta_fast(params, components, observed, nb_votants) == pytest.approx(
        Delta(params, components, observed, nb_votants)
    )


def test_get_linear_parameter_retrouve_un_modele_exact():
    """Données parfaitement affines : le fit doit retrouver pente et ordonnée."""
    donnees = [
        (OUI_ORDONNEE + OUI_PENTE * c1, composante(c1), 1000)
        for c1 in np.linspace(-1.5, 1.5, 20)
    ]

    params = get_linear_parameter(donnees)

    assert params[0] == pytest.approx(OUI_PENTE, abs=1e-4)
    assert params[-1] == pytest.approx(OUI_ORDONNEE, abs=1e-4)
    # Les axes 2 à 6 ne portent aucun signal : leurs coefficients restent nuls.
    assert params[1:-1] == pytest.approx(np.zeros(nb_component - 1), abs=1e-4)


def test_get_linear_parameter_pondere_par_le_nombre_de_bulletins():
    """La pondération par les bulletins rentrés est le cœur de la méthode.

    Avec toutes les composantes nulles, le modèle se réduit à sa constante et
    l'optimum est analytiquement la moyenne *pondérée* des observations — une
    grande commune doit donc peser bien plus qu'une petite.
    """
    observations = [(0.20, 10), (0.80, 990)]
    donnees = [(oui, composante(0.0), poids) for oui, poids in observations]

    params = get_linear_parameter(donnees)

    moyenne_ponderee = sum(oui * poids for oui, poids in observations) / sum(
        poids for _, poids in observations
    )
    assert params[-1] == pytest.approx(moyenne_ponderee, abs=1e-4)
    # Sans pondération, on obtiendrait la moyenne simple (0.50).
    assert params[-1] != pytest.approx(0.50, abs=1e-2)


def test_get_extrapolated_value_applique_le_modele_a_chaque_commune():
    params = np.array([OUI_PENTE, 0.0, 0.0, 0.0, 0.0, 0.0, OUI_ORDONNEE])
    composantes = [composante(c1) for c1 in (-1.0, 0.0, 1.0)]

    valeurs = get_extrapolated_value(composantes, params)

    assert valeurs == pytest.approx([0.40, 0.50, 0.60])


# --------------------------------------------------------------------------- #
# La projection complète, sur une base synthétique
# --------------------------------------------------------------------------- #


def peupler_base_lineaire(nb_communes, nb_comptees):
    """Une soirée de dépouillement où le modèle est exactement vrai.

    Chaque commune reçoit une coordonnée ACP, un nombre d'électeurs, et des
    résultats calculés par le modèle affine ci-dessus. Les communes non
    dépouillées portent quand même leurs vraies valeurs (comme le fait
    ``peupler_demo``), mais ``comptabilise=False`` : la projection ne doit donc
    pas les lire, seulement les reconstruire.

    Renvoie le sujet et le total réel (oui, non) sur *toutes* les communes.
    """
    canton = Canton.objects.create(nom="Vaud", abreviation="VD")
    district = District.objects.create(nom="Lavaux-Oron", numero_ofs=1, canton=canton)
    sujet = SujetVote.objects.create(
        nom="Objet synthétique", sujet_id=1, date=datetime.date(2026, 9, 27)
    )

    total_oui = total_non = 0
    for i, c1 in enumerate(np.linspace(-1.5, 1.5, nb_communes)):
        # Des tailles très différentes : c'est ce qui rend la pondération et
        # l'estimation du nombre de votants observables dans le résultat.
        electeurs = 500 + 250 * i
        votants = round(electeurs * (PART_ORDONNEE + PART_PENTE * c1))
        oui = round(votants * (OUI_ORDONNEE + OUI_PENTE * c1))
        non = votants - oui
        total_oui += oui
        total_non += non

        commune = Commune.objects.create(
            nom=f"Commune {i}", numero_ofs=1000 + i, canton=canton,
            district=district, nb_voix=electeurs,
        )
        PCAResult.objects.create(
            commune=commune,
            **{f"coordinate_{axe + 1}": valeur
               for axe, valeur in enumerate(composante(c1))},
        )
        ScrutinEnCours.objects.create(
            commune=commune, sujet_vote=sujet,
            nombre_oui=oui, nombre_non=non,
            electeurs_inscrits=electeurs, bulletins_rentres=votants,
            electeur_election_precedente=electeurs,
            comptabilise=i < nb_comptees,
        )
    return sujet, total_oui, total_non


@pytest.mark.django_db
def test_extrapolation_retrouve_le_resultat_final_sur_un_modele_exact():
    """Le test le plus parlant : la projection doit tomber sur le vrai résultat.

    Un tiers des communes seulement est dépouillé, et ce sont les plus petites
    (biais volontaire, comme un vrai dimanche de scrutin). Comme le modèle qui
    a engendré les données est exactement celui que la méthode ajuste, la
    projection doit reconstituer le total réel à l'arrondi près.
    """
    sujet, total_oui, total_non = peupler_base_lineaire(nb_communes=40, nb_comptees=13)

    connu, extrapolation, avance, sans_resultat, oui_estime, part_estimee = (
        get_extrapolation(sujet)
    )

    assert extrapolation == pytest.approx(total_oui / (total_oui + total_non), abs=1e-3)
    assert len(sans_resultat) == 40 - 13
    assert len(oui_estime) == len(part_estimee) == 40 - 13
    # Le dépouillement porte sur les 13 plus petites communes : l'avance est
    # donc bien inférieure à la part des communes rentrées (13/40).
    assert 0 < avance < 13 / 40
    # Et le résultat connu est biaisé — c'est précisément ce que la projection
    # corrige, sinon la méthode ne servirait à rien.
    assert connu != pytest.approx(extrapolation, abs=1e-3)


@pytest.mark.django_db
def test_moins_de_sept_communes_depouillees_renvoie_le_repli():
    """Garde-fou : sous 7 communes, on refuse d'ajuster 7 paramètres."""
    sujet, _, _ = peupler_base_lineaire(nb_communes=40, nb_comptees=6)

    connu, extrapolation, avance, sans_resultat, oui_estime, part_estimee = (
        get_extrapolation(sujet)
    )

    assert (connu, extrapolation, avance) == (0.5, 0.5, 0)
    assert sans_resultat == []
    assert oui_estime == []
    assert part_estimee == []


@pytest.mark.django_db
def test_commune_sans_profil_acp_est_signalee():
    """Une commune sans ``PCAResult`` doit lever une erreur explicite.

    C'est la cause racine des exclusions nominatives (Rüti bei Lyssach, Jaberg)
    qui traînent dans les scripts du jour J : le message doit nommer la commune
    fautive pour qu'un soir de scrutin reste diagnosticable.
    """
    sujet, _, _ = peupler_base_lineaire(nb_communes=40, nb_comptees=13)
    PCAResult.objects.filter(commune__nom="Commune 7").delete()

    with pytest.raises(Exception, match="Commune 7"):
        get_extrapolation(sujet)
