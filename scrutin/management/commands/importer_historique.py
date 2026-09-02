"""Reconstruit l'historique communal depuis l'open data fédéral.

L'historique venait de `donnee_federale_v3.txt`, un fichier hors dépôt dont il
ne reste aucune copie sur les machines du projet. Les mêmes résultats sont
publics : un JSON par dimanche de votation, au format déjà lu le jour J.

    curl -O https://app-prod-static-voteinfo.s3.eu-central-1.amazonaws.com/v1/ogd/sd-t-17-02-20210613-eidgAbstimmung.json
    python manage.py importer_historique sd-t-17-02-20210613-eidgAbstimmung.json

Relançable : les résultats sont écrits en `update_or_create`.
"""

import json
import logging

from django.core.management.base import BaseCommand

from scrutin.management.commands.update_scrutin_en_cours import clean_date
from scrutin.models import Commune, ResultatCommunalHistorique, SujetVote

logger = logging.getLogger(__name__)


def importer(chemin):
    """Importe un JSON fédéral. Renvoie (sujets, résultats, communes inconnues)."""
    with open(chemin) as f:
        data = json.load(f)
    date = clean_date(data['abstimmtag'])
    nb_sujets = nb_resultats = 0
    inconnues = set()
    for objet in data['schweiz']['vorlagen']:
        sujet, _ = SujetVote.objects.update_or_create(
            sujet_id=objet['vorlagenId'],
            defaults={"nom": objet['vorlagenTitel'][1]['text'], "date": date},
        )
        nb_sujets += 1
        for canton in objet['kantone']:
            for gemeinde in canton['gemeinden']:
                resultat = gemeinde['resultat']
                if resultat['jaStimmenAbsolut'] is None:
                    continue
                try:
                    commune = Commune.get_unique_commune_by_ofs(gemeinde['geoLevelnummer'])
                except Exception:
                    inconnues.add(gemeinde['geoLevelname'])
                    continue
                ResultatCommunalHistorique.objects.update_or_create(
                    commune=commune,
                    sujet_vote=sujet,
                    defaults={
                        "nombre_oui": resultat['jaStimmenAbsolut'],
                        "nombre_non": resultat['neinStimmenAbsolut'],
                        "electeurs_inscrits": resultat['anzahlStimmberechtigte'],
                        "bulletins_rentres": resultat['eingelegteStimmzettel'],
                    },
                )
                nb_resultats += 1
    return nb_sujets, nb_resultats, inconnues


class Command(BaseCommand):
    help = "Importe un ou plusieurs JSON fédéraux dans l'historique communal."

    def add_arguments(self, parser):
        parser.add_argument("json", nargs="+", help="un fichier par dimanche de votation")

    def handle(self, *args, **options):
        for chemin in options["json"]:
            nb_sujets, nb_resultats, inconnues = importer(chemin)
            self.stdout.write(
                f"{chemin} : {nb_sujets} objets, {nb_resultats} résultats communaux")
            if inconnues:
                logger.warning('%d communes du JSON absentes de la base : %s',
                               len(inconnues), ', '.join(sorted(inconnues)[:5]))
