"""Une seule ligne de scrutin en cours par commune et par objet."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scrutin', '0001_initial'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='resultatcommunalencours',
            constraint=models.UniqueConstraint(fields=('commune', 'sujet_vote'),
                                               name='une_ligne_par_commune_et_objet'),
        ),
    ]
