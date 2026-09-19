"""Les pages du menu : leur contenu est versionné dans ``contenus/`` et recopié
en base par ``manage.py peupler_pages``. Ce fichier fait foi, pas l'admin."""

from pathlib import Path

from page_statique.models import PageStatique

CONTENUS = Path(__file__).resolve().parent / "contenus"

# (adresse, titre dans le menu, ordre) ; le HTML est dans contenus/<adresse>.html.
PAGES = [
    ("contact", "Contact", 1),
]


def peupler_pages():
    """Aligne la base sur PAGES ; renvoie les adresses des pages supprimées."""
    for url, titre, ordre in PAGES:
        PageStatique.objects.update_or_create(url=url, defaults={
            "titre": titre,
            "ordre": ordre,
            "contenu": (CONTENUS / f"{url}.html").read_text(encoding="utf-8"),
        })
    autres = PageStatique.objects.exclude(url__in=[url for url, _, _ in PAGES])
    urls = sorted(autres.values_list("url", flat=True))
    autres.delete()
    return urls
