from django.core.management.base import BaseCommand

from page_statique.pages import PAGES, peupler_pages


class Command(BaseCommand):
    help = "Recopie en base les pages du menu (page_statique/contenus/) et retire les autres."

    def handle(self, *args, **options):
        retirees = peupler_pages()
        self.stdout.write(f"{len(PAGES)} page(s) du menu : {', '.join(url for url, _, _ in PAGES)}")
        if retirees:
            self.stdout.write(f"retirée(s) : {', '.join(retirees)}")
