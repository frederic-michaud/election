from django.core.management.base import BaseCommand

from scrutin.anomalies import SEUIL_COMMUNES, detecter


class Command(BaseCommand):
    help = "Repère les erreurs de saisie probables du scrutin en cours (doc/anomalies.md)."

    def handle(self, *args, **options):
        compte = detecter()
        if not compte:
            self.stdout.write(f"moins de {SEUIL_COMMUNES} communes dépouillées : rien à juger")
            return
        self.stdout.write(", ".join(f"{nombre} {niveau}" for niveau, nombre in compte.items()))
