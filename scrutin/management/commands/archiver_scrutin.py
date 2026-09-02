"""Fait passer les résultats définitifs du jour J dans l'historique.

Une fois le dépouillement terminé, `ResultatCommunalEnCours` contient le
résultat réel de chaque commune : il rejoint `ResultatCommunalHistorique`, et
l'ACP se bonifie d'une votation à chaque scrutin.

**Seules les lignes `comptabilise=True` sont archivées.** `run_extrapolation`
écrit ses estimations dans les lignes des communes non dépouillées : les
archiver reviendrait à nourrir l'ACP avec des chiffres inventés.
"""

from django.core.management.base import BaseCommand

from scrutin.models import ResultatCommunalEnCours, ResultatCommunalHistorique, SujetVote


def archiver(date):
    """Archive les résultats comptabilisés du scrutin. Renvoie (archivés, ignorés)."""
    sujets = SujetVote.objects.filter(date=date)
    lignes = ResultatCommunalEnCours.objects.filter(sujet_vote__in=sujets)
    archives = ignores = 0
    for ligne in lignes.select_related('commune', 'sujet_vote'):
        if not ligne.comptabilise:
            ignores += 1
            continue
        ResultatCommunalHistorique.objects.update_or_create(
            commune=ligne.commune,
            sujet_vote=ligne.sujet_vote,
            defaults={
                "nombre_oui": ligne.nombre_oui,
                "nombre_non": ligne.nombre_non,
                "electeurs_inscrits": ligne.electeurs_inscrits,
                "bulletins_rentres": ligne.bulletins_rentres,
            },
        )
        archives += 1
    return archives, ignores


class Command(BaseCommand):
    help = "Archive les résultats comptabilisés du dernier scrutin dans l'historique."

    def add_arguments(self, parser):
        parser.add_argument("--date", help="Jour du scrutin (AAAA-MM-JJ). Défaut : le plus récent.")

    def handle(self, *args, **options):
        date = options["date"] or SujetVote.objects.latest('date').date
        archives, ignores = archiver(date)
        self.stdout.write(f"{archives} résultats archivés pour le {date}")
        if ignores:
            self.stdout.write(self.style.WARNING(
                f"{ignores} lignes non comptabilisées ignorées : le dépouillement "
                "n'est pas terminé, ou ces valeurs sont des estimations."))
