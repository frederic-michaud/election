import logging

import numpy as np
import scipy.optimize

from pca.models import PCAResult
from scrutin.models import ResultatCommunalEnCours

logger = logging.getLogger(__name__)

nb_component = 6

COORDONNEES = ('coordinate_1', 'coordinate_2', 'coordinate_3',
               'coordinate_4', 'coordinate_5', 'coordinate_6')


def profils_de_repli():
    """Profil moyen par district, et profil moyen national.

    Doublure pour les communes absentes de l'ACP. Il y en a toujours : une
    commune à l'historique incomplet en est écartée, et c'est le cas de celles
    qui viennent d'être publiées séparément après avoir voté à l'urne d'une
    voisine. Leur prêter le profil moyen de leurs voisines vaut mieux que de
    les ignorer, et bien mieux que de faire tomber la projection.

    Les composantes étant centrées, la moyenne nationale vaut à peu près zéro :
    une commune sans district connu est donc traitée comme une commune
    moyenne, le pari le moins aventureux.
    """
    par_district = {}
    tous = []
    for district_id, *coordonnees in PCAResult.objects.values_list(
            'commune__district_id', *COORDONNEES):
        profil = list(coordonnees[:nb_component])
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