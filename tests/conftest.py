import json

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


@pytest.fixture
def ecrire_scrutin():
    """Fabrique un JSON fédéral minimal, au format du jour J.

    ``objets`` est une liste (un élément par objet de votation) de dicts
    ``{numero_ofs: dépouillée ou non}``. Partagé entre les tests d'import et
    ceux de la répétition générale : c'est le même gabarit qui sert à vérifier
    la détection des nouvelles communes et l'emboîtement des instantanés.
    """
    def ecrire(chemin, objets):
        data = {"schweiz": {"vorlagen": [
            {
                "vorlagenId": index + 1,
                "kantone": [{"gemeinden": [
                    {
                        "geoLevelnummer": ofs,
                        "geoLevelname": f"Commune {ofs}",
                        "resultat": {"jaStimmenAbsolut": 100 if depouillee else None},
                    }
                    for ofs, depouillee in communes.items()
                ]}],
            }
            for index, communes in enumerate(objets)
        ]}}
        chemin.write_text(json.dumps(data))
        return chemin

    return ecrire
