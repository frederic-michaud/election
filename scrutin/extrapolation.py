from scrutin.models import ScrutinEnCours, Commune, SujetVote
from pca.models import PCAResult
import numpy as np
import scipy.optimize

nb_component = 6

def get_percentage(component, params):
    return np.sum(component * params[:-1]) + params[-1]

def Delta(params, data_all_commune):
    extrapolation = [get_percentage(component, params) for _, component in data_all_commune]
    observed = [percentage for percentage, _ in data_all_commune]
    return np.sum(np.square(np.array(extrapolation) - np.array(observed)))

def get_linear_parameter(data_all_commune):
    x_init = np.full(nb_component + 1, 0.)
    x_init[-1] = 0.5
    extrapolated_param = scipy.optimize.minimize(Delta, x_init, args=data_all_commune)
    return extrapolated_param.x

def get_extrapolated_value(components, params):
    return np.array([get_percentage(component, params) for component in components])


def get_extrapolation(sujet):
    know_result_oui = 0
    know_result_non = 0
    data_to_interpolate = []
    data_for_interpolating_pourcentage_oui = []
    data_for_interpolating_participation = []
    nbre_votant_appxoximated = []
    for voix in ScrutinEnCours.objects.filter(sujet_vote = sujet):
        pca = PCAResult.objects.filter(commune=voix.commune)
        if (len(pca) != 1):
            raise Exception('Commune pca not found')
        pca = pca[0]
        if voix.comptabilise:
            data_for_interpolating_pourcentage_oui.append((voix.get_pourcentage_oui(), pca.get_component(nb_component)))
            data_for_interpolating_participation.append((voix.get_real_participation(), pca.get_component(nb_component)))
            know_result_oui += voix.nombre_oui
            know_result_non += voix.nombre_non
        else:
            data_to_interpolate.append(pca.get_component(nb_component))
            nbre_votant_appxoximated.append(voix.electeur_election_precedente)
    if len(data_for_interpolating_participation) < 7:
        return 0.5, 0.5

    nbre_votant_appxoximated = np.array(nbre_votant_appxoximated)
    params_pourcentage_oui = get_linear_parameter(data_for_interpolating_pourcentage_oui)
    params_participation = get_linear_parameter(data_for_interpolating_participation)
    extrapolated_pourcentage_oui = get_extrapolated_value(data_to_interpolate, params_pourcentage_oui)
    extrapolated_participation = get_extrapolated_value(data_to_interpolate, params_participation)
    nbre_oui_extrapolated = np.sum(extrapolated_pourcentage_oui * extrapolated_participation * nbre_votant_appxoximated)
    nbre_non_extrapolated = np.sum((1 - extrapolated_pourcentage_oui) * extrapolated_participation * nbre_votant_appxoximated)
    nbre_oui_final = nbre_oui_extrapolated + know_result_oui
    nbre_non_final = nbre_non_extrapolated + know_result_non


    extrapolation = nbre_oui_extrapolated/(nbre_oui_extrapolated + nbre_non_extrapolated)
    current = know_result_oui/(know_result_oui + know_result_non)
    return current, extrapolation