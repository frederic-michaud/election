import logging

import numpy as np
import scipy.optimize

from pca.models import NB_AXES, PCAResult
from scrutin.models import ResultatCommunalEnCours

logger = logging.getLogger(__name__)

nb_component = NB_AXES

# En dessous, la projection fait pire que le dépouillement brut (doc/backtest.md).
SEUIL_COMMUNES = 50

# Demi-largeur de la fourchette selon l'avance, en points : 95 % des
# projections du backtest tombent à moins de cet écart du résultat final
# (doc/backtest.md). À recalculer quand le modèle change.
FOURCHETTE = (
    (0.003, 5.5), (0.005, 4.3), (0.0075, 3.9), (0.01, 3.4), (0.02, 2.9),
    (0.03, 2.6), (0.05, 2.2), (0.10, 1.7), (0.15, 1.5), (0.20, 1.3),
    (0.25, 1.2), (0.30, 1.0), (0.40, 0.9), (0.50, 0.7), (0.60, 0.6),
    (0.70, 0.5), (0.80, 0.4), (0.90, 0.3), (0.95, 0.2), (1.00, 0.0),
)


def demi_fourchette(avance):
    """Demi-largeur de la fourchette, en part de oui (0.012 pour 1,2 point)."""
    avances, points = zip(*FOURCHETTE)
    return float(np.interp(avance, avances, points)) / 100


def profils_de_repli():
    """Profil moyen par district, et profil moyen national.

    Doublure pour les communes absentes de l'ACP. Il y en a toujours : une
    commune à l'historique incomplet en est écartée, et c'est le cas de celles
    qui viennent d'être publiées séparément après avoir voté à l'urne d'une
    voisine. Leur prêter le profil moyen de leurs voisines vaut mieux que de
    les ignorer, et bien mieux que de faire tomber la projection.

    Une commune sans district connu est traitée comme une commune moyenne,
    le pari le moins aventureux.
    """
    par_district = {}
    tous = []
    for pca_result in PCAResult.objects.select_related('commune'):
        district_id = pca_result.commune.district_id
        profil = pca_result.get_component(nb_component)
        par_district.setdefault(district_id, []).append(profil)
        tous.append(profil)
    if not tous:
        return {}, [0.0] * nb_component
    moyennes = {district_id: list(np.mean(profils, axis=0))
                for district_id, profils in par_district.items()}
    return moyennes, list(np.mean(tous, axis=0))

def get_percentage(component, params):
    return np.sum(component * params[:-1]) + params[-1]

def Delta(params, components, observed, nb_votants):
    extrapolation = [get_percentage(component, params) for component in components]
    return np.sum(np.square(np.array(extrapolation) - np.array(observed))*nb_votants)

def Delta_fast(params, components, observed, nb_votants):
    extrapolation = np.sum(components*params[:-1], axis = 1) + params[-1]
    return np.sum(np.square(np.array(extrapolation) - np.array(observed))*nb_votants)


def get_linear_parameter(data_all_commune):
    x_init = np.full(nb_component + 1, 0.)
    x_init[-1] = 0.5
    components = [component for _, component, _ in data_all_commune]
    observed = [percentage for percentage, _, _ in data_all_commune]
    nb_votants = [nb_votant for _, _, nb_votant in data_all_commune]
    extrapolated_param = scipy.optimize.minimize(Delta_fast, x_init, args=(components, observed, nb_votants))
    return extrapolated_param.x

def get_extrapolated_value(components, params):
    return np.array([get_percentage(component, params) for component in components])


def get_extrapolation(sujet):
    know_result_oui = 0
    know_result_non = 0
    data_to_interpolate = []
    data_for_interpolating_pourcentage_oui = []
    data_for_interpolating_participation = []
    nbre_votant_approximated = []
    commune_without_result = []
    profils = {
        pca_result.commune_id: pca_result.get_component(nb_component)
        for pca_result in PCAResult.objects.all()
    }
    par_district, national = profils_de_repli()
    for voix in (ResultatCommunalEnCours.objects.filter(sujet_vote=sujet)
                 .select_related('commune').order_by("commune")):
        profil = profils.get(voix.commune_id)
        if voix.comptabilise:
            # Ses bulletins sont réels : ils comptent, profil ou pas.
            know_result_oui += voix.nombre_oui
            know_result_non += voix.nombre_non
            if profil is None:
                # Sans profil, elle ne peut pas servir de point d'appui au
                # modèle : un profil de repli fausserait l'ajustement.
                logger.warning("%s n'a pas de profil ACP : ses bulletins sont "
                               "comptés, mais elle ne sert pas à ajuster le modèle",
                               voix.commune)
                continue
            data_for_interpolating_pourcentage_oui.append((voix.get_pourcentage_oui(), profil, voix.bulletins_rentres))
            data_for_interpolating_participation.append((voix.get_real_participation(), profil, voix.bulletins_rentres))
        else:
            if profil is None:
                profil = par_district.get(voix.commune.district_id, national)
                logger.warning("%s n'a pas de profil ACP : projetée avec le "
                               "profil moyen de son district", voix.commune)
            data_to_interpolate.append(profil)
            nbre_votant_approximated.append(voix.electeur_election_precedente)
            commune_without_result.append(voix)
    if len(data_for_interpolating_participation) < SEUIL_COMMUNES:
        return None, None, 0.0, [], [], []
    nbre_votant_approximated = np.array(nbre_votant_approximated)
    params_pourcentage_oui = get_linear_parameter(data_for_interpolating_pourcentage_oui)
    params_participation = get_linear_parameter(data_for_interpolating_participation)
    extrapolated_pourcentage_oui = get_extrapolated_value(data_to_interpolate, params_pourcentage_oui)
    extrapolated_participation = get_extrapolated_value(data_to_interpolate, params_participation)
    nbre_oui_extrapolated = np.sum(extrapolated_pourcentage_oui * extrapolated_participation * nbre_votant_approximated)
    nbre_non_extrapolated = np.sum((1 - extrapolated_pourcentage_oui) * extrapolated_participation * nbre_votant_approximated)
    nbre_oui_final = nbre_oui_extrapolated + know_result_oui
    nbre_non_final = nbre_non_extrapolated + know_result_non
    extrapolation = nbre_oui_final/(nbre_oui_final + nbre_non_final)
    current = know_result_oui/(know_result_oui + know_result_non)
    avance = (know_result_oui + know_result_non)/(nbre_oui_final + nbre_non_final)
    return current, extrapolation, avance, commune_without_result, extrapolated_pourcentage_oui, extrapolated_participation