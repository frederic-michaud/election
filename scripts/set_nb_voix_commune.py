from scrutin.models import Commune


def set_commune_nb_voix():
    for commune in Commune.objects.all():
        commune.set_voix()
        commune.save()




def run():
    set_commune_nb_voix()