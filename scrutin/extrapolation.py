from scrutin.models import ScrutinEnCours, Commune, SujetVote
from pca.models import PCAResult
import numpy as np
import scipy.optimize
nb_component = 6

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
    PCAResult_dict = {
        pca_result.commune_id: pca_result
        for pca_result in PCAResult.objects.all()
    }
    for voix in ScrutinEnCours.objects.filter(sujet_vote = sujet).order_by("commune"):
        try:
            pca = PCAResult_dict[voix.commune_id]
        except:
            raise Exception('Commune pca not found')
        if voix.comptabilise:
            data_for_interpolating_pourcentage_oui.append((voix.get_pourcentage_oui(), pca.get_component(nb_component), voix.bulletins_rentres))
            data_for_interpolating_participation.append((voix.get_real_participation(), pca.get_component(nb_component), voix.bulletins_rentres))
            know_result_oui += voix.nombre_oui
            know_result_non += voix.nombre_non
        else:
            data_to_interpolate.append(pca.get_component(nb_component))
            nbre_votant_approximated.append(voix.electeur_election_precedente)
            commune_without_result.append(voix)
    if len(data_for_interpolating_participation) < 7:
        return 0.5, 0.5, 0, [], [], []
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