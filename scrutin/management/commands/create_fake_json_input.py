import json
import logging

import numpy as np
from django.core.management.base import BaseCommand

from scrutin.models import Commune, ResultatCommunalHistorique, SujetVote

logger = logging.getLogger(__name__)


def get_result(commune, sujet):
    voixs = ResultatCommunalHistorique.objects.filter(commune = commune, sujet_vote = sujet)
    if len(voixs) > 0:
        return voixs[0]
    return None


class Command(BaseCommand):
    help = "Fabrique un JSON de test en rejouant d'anciens résultats sur une part des communes."

    def add_arguments(self, parser):
        parser.add_argument("json_du_scrutin")
        parser.add_argument("json_de_sortie", nargs="?", default="json_fake.json")
        parser.add_argument("--fraction", type=float, default=0.05,
                            help="part des communes dépouillées (défaut : 0.05)")

    def handle(self, *args, **options):
        fabriquer(options["json_du_scrutin"], options["json_de_sortie"],
                  options["fraction"])


def fabriquer(path_votation, path_sortie, fraction=0.05):
    """Rejoue d'anciens résultats sur `fraction` des communes.

    La graine est fixe et le tirage est comparé à `fraction` : les communes
    retenues à 5 % le sont encore à 25 %. Deux appels à des fractions
    croissantes donnent donc des instantanés emboîtés, comme une vraie soirée
    où une commune dépouillée le reste — c'est ce qui permet d'enchaîner
    `update_scrutin_en_cours` d'un fichier au suivant.
    """
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
                resultat_previous = get_result(commune, sujet)
                if resultat_previous is None:
                    continue
                if np.random.random() < fraction:
                    resultat_json = data_commune['resultat']
                    resultat_json["jaStimmenAbsolut"] = resultat_previous.nombre_oui
                    resultat_json["neinStimmenAbsolut"] = resultat_previous.nombre_non
                    resultat_json["anzahlStimmberechtigte"] = resultat_previous.electeurs_inscrits
                    resultat_json["eingelegteStimmzettel"] = resultat_previous.bulletins_rentres

    with open(path_sortie, 'w') as f:
        json.dump(data, f)
