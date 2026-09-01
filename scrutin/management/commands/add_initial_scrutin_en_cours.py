import json
import logging

from django.core.management.base import BaseCommand

from scrutin.models import Commune, ResultatCommunalEnCours, SujetVote

logger = logging.getLogger(__name__)


def clean_date(date_str):
    return f'{date_str[0:4]}-{date_str[4:6]}-{date_str[6:8]}'

def import_votation(path_votation):
    with open(path_votation, 'r') as f:
        data = json.load(f)
    for sujet_vote in data['schweiz']['vorlagen']:
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
        for data_canton in sujet_vote['kantone']:
            for data_commune in data_canton['gemeinden']:
                try:
                    commune = Commune.get_unique_commune_by_ofs(data_commune['geoLevelnummer'])
                except Exception:
                    logger.warning('Commune not found: %s: %s',
                                   data_commune["geoLevelnummer"], data_commune["geoLevelname"])
                    continue
                if (commune.nom in ['Rüti bei Lyssach', 'Jaberg']):
                    continue
                ResultatCommunalEnCours.objects.get_or_create(
                    commune=commune,
                    sujet_vote=sujet,
                    defaults={"electeur_election_precedente": commune.nb_voix},
                )

class Command(BaseCommand):
    help = "Sème les lignes vides du jour J depuis le premier JSON fédéral."

    def add_arguments(self, parser):
        parser.add_argument("json_du_scrutin")

    def handle(self, *args, **options):
        ResultatCommunalEnCours.objects.all().delete()
        import_votation(options["json_du_scrutin"])

