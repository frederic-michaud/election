import json
import logging

import numpy as np

from scrutin.models import Commune, ResultatCommunalHistorique, SujetVote

logger = logging.getLogger(__name__)

p_rejection = 0.95

def get_result(commune, sujet):
    voixs = ResultatCommunalHistorique.objects.filter(commune = commune, sujet_vote = sujet)
    if len(voixs) > 0:
        return voixs[0]
    return None


def run(*args):
    if not args:
        raise SystemExit("usage: runscript create_fake_json_input "
                         "--script-args <json_du_scrutin> [<json_de_sortie>]")
    path_votation = args[0]
    path_sortie = args[1] if len(args) > 1 else "json_fake.json"
    sujets = SujetVote.objects.order_by("date")
    with open(path_votation, 'r') as f:
        data = json.load(f)
    for index_sujet, sujet_vote_json in enumerate(data['schweiz']['vorlagen']):
        np.random.seed(0)
        sujet = sujets[index_sujet]
        for data_canton in sujet_vote_json['kantone']:
            for data_commune in data_canton['gemeinden']:
                try:
                    commune = Commune.get_unique_commune_by_ofs(data_commune['geoLevelnummer'])
                except Exception:
                    logger.warning('Commune not found: %s: %s',
                                   data_commune["geoLevelnummer"], data_commune["geoLevelname"])
                    continue
                if (commune.nom in ['Rüti bei Lyssach', 'Jaberg']):
                    continue
                resultat_previous = get_result(commune, sujet)
                if resultat_previous is None:
                    continue
                if np.random.random() > p_rejection:
                    resultat_json = data_commune['resultat']
                    resultat_json["jaStimmenAbsolut"] = resultat_previous.nombre_oui
                    resultat_json["neinStimmenAbsolut"] = resultat_previous.nombre_non
                    resultat_json["anzahlStimmberechtigte"] = resultat_previous.electeurs_inscrits
                    resultat_json["eingelegteStimmzettel"] = resultat_previous.bulletins_rentres

    with open(path_sortie, 'w') as f:
        json.dump(data, f)
