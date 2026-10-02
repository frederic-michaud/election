import json
import logging

from django.core.management.base import BaseCommand
from django.db import transaction

from scrutin.models import Commune, ResultatCommunalEnCours, SujetVote

logger = logging.getLogger(__name__)


def clean_date(date_str):
    return f'{date_str[0:4]}-{date_str[4:6]}-{date_str[6:8]}'

def communes_depouillees(sujet_json):
    """Communes au dépouillement terminé pour cet objet.

    Une grande ville publie des résultats partiels en cours de soirée :
    `jaStimmenAbsolut` est rempli avant la fin du dépouillement. Seul
    `gebietAusgezaehlt` dit qu'il est fini.
    """
    return {
        data_commune['geoLevelnummer']
        for data_canton in sujet_json['kantone']
        for data_commune in data_canton['gemeinden']
        if data_commune['resultat']["gebietAusgezaehlt"]
    }

@transaction.atomic
def import_votation(path_votation):
    """Réimporte toutes les communes dépouillées, objet par objet.

    Tout le scrutin passe en 2,5 s : réimporter à chaque tour reprend aussi
    une correction publiée après coup, qu'un import des seules communes
    nouvelles laissait figée.
    """
    with open(path_votation, 'r') as f:
        data = json.load(f)
    for sujet_vote in data['schweiz']['vorlagen']:
        depouillees = communes_depouillees(sujet_vote)
        sujets = SujetVote.objects.filter(sujet_id = sujet_vote['vorlagenId'])
        if len(sujets) == 1:
            sujet = sujets[0]
        elif len(sujets) == 0:
            sujet = SujetVote(nom = sujet_vote['vorlagenTitel'][1]['text'],
                              sujet_id =  sujet_vote['vorlagenId'],
                              date = clean_date(data['abstimmtag']))
        else:
            raise Exception(f'There is more than one subject with id {sujet_vote["vorlagenId"]}')
        sujet.save()
        logger.info('%s : %d communes dépouillées', sujet, len(depouillees))
        for data_canton in sujet_vote['kantone']:
            for data_commune in data_canton['gemeinden']:
                if data_commune['geoLevelnummer'] not in depouillees:
                    continue
                try:
                    commune = Commune.get_unique_commune_by_ofs(data_commune['geoLevelnummer'])
                except Exception:
                    logger.warning('Commune not found: %s: %s',
                                   data_commune["geoLevelnummer"], data_commune["geoLevelname"])
                    continue
                result = data_commune['resultat']
                ResultatCommunalEnCours.objects.update_or_create(
                    commune=commune,
                    sujet_vote=sujet,
                    defaults={
                        "electeur_election_precedente": commune.nb_voix,
                        "nombre_oui": result["jaStimmenAbsolut"],
                        "nombre_non": result["neinStimmenAbsolut"],
                        "electeurs_inscrits": result["anzahlStimmberechtigte"],
                        "bulletins_rentres": result["eingelegteStimmzettel"],
                        "comptabilise": True,
                    },
                )

class Command(BaseCommand):
    help = "Réimporte toutes les communes dépouillées d'un instantané JSON."

    def add_arguments(self, parser):
        parser.add_argument("json_courant")

    def handle(self, *args, **options):
        import_votation(options["json_courant"])
