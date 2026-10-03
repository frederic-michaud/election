from django.db import migrations, models

ANCIENNES = [f"coordinate_{i}" for i in range(1, 7)]


def regrouper(apps, schema_editor):
    PCAResult = apps.get_model("pca", "PCAResult")
    profils = list(PCAResult.objects.all())
    for profil in profils:
        profil.coordonnees = [getattr(profil, nom) for nom in ANCIENNES]
    PCAResult.objects.bulk_update(profils, ["coordonnees"], batch_size=1000)


class Migration(migrations.Migration):

    dependencies = [
        ("pca", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="pcaresult",
            name="coordonnees",
            field=models.JSONField(default=list),
            preserve_default=False,
        ),
        migrations.RunPython(regrouper, migrations.RunPython.noop),
        *[migrations.RemoveField(model_name="pcaresult", name=nom) for nom in ANCIENNES],
    ]
