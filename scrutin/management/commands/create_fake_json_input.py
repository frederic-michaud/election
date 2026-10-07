import hashlib
import json
import logging

from django.core.management.base import BaseCommand

from scrutin.models import Commune, ResultatCommunalHistorique, SujetVote

logger = logging.getLogger(__name__)


def tirage(numero_ofs):
    """Tirage déterministe dans [0, 1), propre à la commune.

    Un tirage séquentiel serait décalé par chaque commune sans historique, et
    les objets d'un même scrutin ne retiendraient plus les mêmes communes.
    """
    empreinte = hashlib.md5(str(numero_ofs).encode()).digest()
    return int.from_bytes(empreinte[:8], "big") / 2**64


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

    Le tirage est propre à la commune et comparé à `fraction` : les communes
    retenues à 5 % le sont encore à 25 %, et pour tous les objets. Deux appels
    à des fractions croissantes donnent donc des instantanés emboîtés, comme
    une vraie soirée où une commune dépouillée le reste.
    """
    sujets = SujetVote.objects.order_by("date")
    with open(path_votation, 'r') as f:
        data = json.load(f)
    for index_sujet, sujet_vote_json in enumerate(data['schweiz']['vorlagen']):
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
                if tirage(data_commune['geoLevelnummer']) < fraction:
                    resultat_json = data_commune['resultat']
                    resultat_json["gebietAusgezaehlt"] = True
                    resultat_json["jaStimmenAbsolut"] = resultat_previous.nombre_oui
                    resultat_json["neinStimmenAbsolut"] = resultat_previous.nombre_non
                    resultat_json["anzahlStimmberechtigte"] = resultat_previous.electeurs_inscrits
                    resultat_json["eingelegteStimmzettel"] = resultat_previous.bulletins_rentres

    with open(path_sortie, 'w') as f:
        json.dump(data, f)
