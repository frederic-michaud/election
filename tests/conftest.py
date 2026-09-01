import pytest
from django.core.management import call_command


@pytest.fixture(scope="module")
def base_demo(django_db_setup, django_db_blocker):
    """Peuple la base de démonstration une seule fois pour tout le module."""
    with django_db_blocker.unblock():
        call_command("peupler_demo", verbosity=0)
        yield
        # peupler_demo écrit hors du rollback de pytest-django : sans ce
        # nettoyage, ses 2 141 communes fuient dans les modules suivants.
        call_command("flush", "--no-input", verbosity=0)
