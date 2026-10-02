import json
import logging

from django.core.management.base import BaseCommand

from scrutin.models import Commune, ResultatCommunalEnCours, SujetVote

logger = logging.getLogger(__name__)


def clean_date(date_str):
    return f'{date_str[0:4]}-{date_str[4:6]}-{date_str[6:8]}'

def communes_depouillees(sujet_json):
    """Communes au dépouillement terminé pour cet objet.

    Une grande ville publie des résultats partiels en cours de soirée :
    `jaStimmenAbsolut` est alors rempli alors que le dépouillement n'est pas
    fini. Seul `gebietAusgezaehlt` dit qu'il l'est.
    """
    return {
        data_commune['geoLevelnummer']
        for data_canton in sujet_json['kantone']
        for data_commune in data_canton['gemeinden']
        if data_commune['resultat']["gebietAusgezaehlt"]
    }

def communes_completes(data):
    """Communes dépouillées pour *tous* les objets du scrutin."""
    return set.intersection(*(communes_depouillees(sujet)
                              for sujet in data['schweiz']['vorlagen']))

def get_new_commune(path_previous, path_current):
    """Communes complètes dans l'instantané courant, pas dans le précédent.

    Une commune rentrée pour un objet à un tour et pour l'autre au tour
    suivant n'est nouvelle pour aucun objet pris un à un : il faut comparer
    les communes complètes, sinon elle n'est jamais importée.
    """
    with open(path_previous, 'r') as f:
        data_old = json.load(f)
    with open(path_current, 'r') as f:
        data_new = json.load(f)
    return communes_completes(data_new) - communes_completes(data_old)

def import_votation(path_votation, commune_to_import):
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
                if data_commune['geoLevelnummer'] not in commune_to_import:
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
    help = "Importe les communes nouvellement dépouillées entre deux instantanés JSON."

    def add_arguments(self, parser):
        parser.add_argument("json_precedent")
        parser.add_argument("json_courant")

    def handle(self, *args, **options):
        commune_to_import = get_new_commune(options["json_precedent"], options["json_courant"])
        logger.info('%d nouvelles communes dépouillées : %s',
                    len(commune_to_import), sorted(commune_to_import))
        import_votation(options["json_courant"], commune_to_import)

