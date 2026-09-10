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
    profils_de_repli,
)
from scrutin.models import Canton, Commune, District, ResultatCommunalEnCours, SujetVote

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
    district = District.objects.create(nom="Lavaux-Oron", code_historique=1, canton=canton)
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
        ResultatCommunalEnCours.objects.create(
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
def test_une_commune_sans_profil_ne_fait_pas_tomber_la_projection(caplog):
    """Le scénario qui gelait la soirée.

    Une commune sans ``PCAResult`` levait une exception, donc plus aucune
    projection jusqu'à ce que quelqu'un s'en aperçoive. C'est arrivé pour de
    vrai : une commune qui se met à publier ses résultats séparément n'a pas
    d'historique, donc pas de profil. Elle est désormais projetée avec le
    profil moyen de son district, et l'avertissement la nomme.
    """
    sujet, oui_reel, non_reel = peupler_base_lineaire(nb_communes=40, nb_comptees=13)
    # Une commune pas encore dépouillée : c'est elle qu'il faut projeter.
    PCAResult.objects.filter(commune__nom="Commune 20").delete()

    _, extrapolation, _, sans_resultat, _, _ = get_extrapolation(sujet)

    assert "Commune 20" in caplog.text
    # Elle est projetée comme les autres, pas laissée de côté.
    assert "Commune 20" in [voix.commune.nom for voix in sans_resultat]
    assert extrapolation == pytest.approx(oui_reel / (oui_reel + non_reel), abs=0.01)


@pytest.mark.django_db
def test_les_bulletins_d_une_commune_comptee_sans_profil_sont_comptes(caplog):
    """Ses voix sont réelles : elles entrent dans le dépouillement connu.

    Elle ne peut pas servir de point d'appui au modèle — un profil inventé
    fausserait l'ajustement — mais l'ignorer perdrait de vrais bulletins, ce
    que faisaient les exclusions nominatives des scripts du jour J.
    """
    sujet, _, _ = peupler_base_lineaire(nb_communes=40, nb_comptees=13)
    comptee = ResultatCommunalEnCours.objects.filter(
        sujet_vote=sujet, comptabilise=True).order_by("commune").first()
    PCAResult.objects.filter(commune=comptee.commune).delete()

    connu, _, _, _, _, _ = get_extrapolation(sujet)

    assert comptee.commune.nom in caplog.text
    lignes = ResultatCommunalEnCours.objects.filter(sujet_vote=sujet, comptabilise=True)
    oui = sum(ligne.nombre_oui for ligne in lignes)
    non = sum(ligne.nombre_non for ligne in lignes)
    assert connu == pytest.approx(oui / (oui + non))


@pytest.mark.django_db
def test_le_profil_de_repli_est_la_moyenne_du_district():
    """Deux districts aux profils opposés : le repli doit prendre le bon."""
    peupler_base_lineaire(nb_communes=4, nb_comptees=4)
    district = District.objects.get()
    autre = District.objects.create(nom="Ailleurs", code_historique=2,
                                    canton=district.canton)
    lointaine = Commune.objects.create(nom="Lointaine", numero_ofs=9999,
                                       canton=district.canton, district=autre)
    PCAResult.objects.create(commune=lointaine, coordinate_1=10.0, coordinate_2=0.0,
                             coordinate_3=0.0, coordinate_4=0.0, coordinate_5=0.0,
                             coordinate_6=0.0)

    par_district, national = profils_de_repli()

    assert par_district[autre.id][0] == pytest.approx(10.0)
    # Les quatre communes du premier district sont réparties de -1,5 à 1,5.
    assert par_district[district.id][0] == pytest.approx(0.0)
    assert national[0] == pytest.approx(10.0 / 5)
