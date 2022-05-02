from scrutin.models import ScrutinEnCours, Commune
from pca.models import PCAResult
import numpy as np
import scipy.optimize

nb_component = 6

def get_percentage(component, params):
    return np.sum(component * params[:-1] + params[-1])

def get_linear_parameter(data):
    def Delta(params, data_interpolation):
        extrapolation = [get_percentage(component[1], params) for component in data_interpolation]
        donnee = [data[0] for data in data]
        return np.sum(np.square(np.array(extrapolation) - np.array(donnee)))

    x_init = np.full(nb_component + 1, 0.5)
    extrapolated_param = scipy.optimize.minimize(Delta, x_init, args=data)


def get_extrapolation():
    sujet = ScrutinEnCours.objects[0]

    for voix in ScrutinEnCours.objects.filter(sujet = sujet):
        data_for_interpolating_pourcentage = []
        data_for_interpolating_participation = []
        if voix.is_valid:
            pca = PCAResult.objects.filter(commune = voix.commune)
            data_for_interpolating_pourcentage.append((voix.get_pourcentage_oui, pca.get_component(nb_component)))
            data_for_interpolating_participation.append(voix.get_participation())





        extrapolation = np.array([get_percentage(component, extrapolated_param.x) for component in X_reduced[:,0:nb_component]])

    return 0.5