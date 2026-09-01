import json
import logging

import numpy as np
from django.core.management.base import BaseCommand

from scrutin.models import Commune, ResultatCommunalHistorique, SujetVote

logger = logging.getLogger(__name__)

p_rejection = 0.95

def get_result(commune, sujet):
    voixs = ResultatCommunalHistorique.objects.filter(commune = commune, sujet_vote = sujet)
    if len(voixs) > 0:
        return voixs[0]
    return None


class Command(BaseCommand):
    help = "Fabrique un JSON de test en rejouant d'anciens résultats sur 5 % des communes."

    def add_arguments(self, parser):
        parser.add_argument("json_du_scrutin")
        parser.add_argument("json_de_sortie", nargs="?", default="json_fake.json")

    def handle(self, *args, **options):
        fabriquer(options["json_du_scrutin"], options["json_de_sortie"])


def fabriquer(path_votation, path_sortie):
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
