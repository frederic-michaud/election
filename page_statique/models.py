from django.db import models


# Create your models here.
class PageStatique(models.Model):
    titre = models.CharField(max_length=400)
    contenu = models.TextField()
    url = models.CharField(max_length=50)
    ordre = models.IntegerField(default=0, help_text="Ordre d'affichage dans le menu.")

    class Meta:
        ordering = ["ordre", "titre"]
    def  __str__(self):
        return self.titre