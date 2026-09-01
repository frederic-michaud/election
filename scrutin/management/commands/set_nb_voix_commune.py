from django.core.management.base import BaseCommand

from scrutin.models import Commune


def set_commune_nb_voix():
    for commune in Commune.objects.all():
        commune.set_voix()
        commune.save()




class Command(BaseCommand):
    help = "Commune.nb_voix = électeurs inscrits à la dernière votation."

    def handle(self, *args, **options):
        set_commune_nb_voix()
