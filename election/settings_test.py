"""Réglages utilisés par la suite de tests.

Les réglages de production refusent de démarrer sans ``SECRET_KEY`` — c'est
voulu. On active donc ``DEBUG`` **avant** de les importer, ce qui suffit à leur
faire prendre la clé de développement : la suite se lance ainsi depuis un clone
frais et dans la CI, sans fichier ``.env`` ni configuration préalable.

pytest-django appelle ``django.setup()`` avant de charger les ``conftest.py``,
d'où ce module plutôt qu'une variable posée dans un conftest.
"""

import os

os.environ.setdefault("DEBUG", "1")

from election.settings import *  # noqa: E402,F403
