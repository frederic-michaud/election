"""Une seule ligne de scrutin en cours par commune et par objet.

L'invariant n'était tenu que par le code. Une base existante peut donc porter
des doublons hérités de l'époque où `update_scrutin_en_cours` créait une
seconde ligne au lieu de remplir la première : on les résorbe avant de poser
la contrainte, sinon la migration échouerait au lieu de réparer.
"""

from django.db import migrations, models


def resorber_les_doublons(apps, schema_editor):
    ResultatCommunalEnCours = apps.get_model('scrutin', 'ResultatCommunalEnCours')
    vus = {}
    a_supprimer = []
    for ligne in ResultatCommunalEnCours.objects.order_by('id'):
        cle = (ligne.commune_id, ligne.sujet_vote_id)
        garde = vus.get(cle)
        if garde is None:
            vus[cle] = ligne
        elif meilleure(ligne, garde):
            # On garde la ligne dépouillée, ou à défaut celle qui porte des
            # chiffres : la ligne vide est celle qu'on peut jeter.
            a_supprimer.append(garde.id)
            vus[cle] = ligne
        else:
            a_supprimer.append(ligne.id)
    ResultatCommunalEnCours.objects.filter(id__in=a_supprimer).delete()


def meilleure(ligne, autre):
    return (ligne.comptabilise, ligne.nombre_oui is not None) > \
           (autre.comptabilise, autre.nombre_oui is not None)


class Migration(migrations.Migration):

    dependencies = [
        ('scrutin', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(resorber_les_doublons, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='resultatcommunalencours',
            constraint=models.UniqueConstraint(fields=('commune', 'sujet_vote'),
                                               name='une_ligne_par_commune_et_objet'),
        ),
    ]
