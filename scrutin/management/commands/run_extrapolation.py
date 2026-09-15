import logging

from django.core.management.base import BaseCommand

from scrutin.extrapolation import get_extrapolation
from scrutin.models import Extrapolation, SujetVote

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Extrapole les communes manquantes et enregistre un instantané Extrapolation."

    def handle(self, *args, **options):
        run()


def run():
    last_sujet = SujetVote.objects.latest('date')
    sujets = SujetVote.objects.filter(date = last_sujet.date)
    for sujet in sujets:
        deja_comptabilise, extrapole, avance, voixs, percent_oui, percent_vote = get_extrapolation(sujet)
        if extrapole is None:
            logger.info("%s : moins de sept communes dépouillées, pas de projection", sujet)
            continue
        for voix, extrapolation_oui, extrapolation_voters in zip(voixs, percent_oui, percent_vote):
            voix.nombre_oui = extrapolation_oui*extrapolation_voters*voix.electeur_election_precedente
            voix.bulletins_rentres = extrapolation_voters * voix.electeur_election_precedente
            voix.nombre_non = voix.bulletins_rentres - voix.nombre_oui
            voix.save()
        extrapolation = Extrapolation(sujet_vote=sujet, pourcentage_oui_connu=deja_comptabilise,
                                      pourcentage_oui_extrapole=extrapole, avance=avance)
        extrapolation.save()