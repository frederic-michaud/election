from django.db import models

# Create your models here.
class PageStatique(models.Model):
    titre = models.CharField(max_length=400)
    contenu = models.TextField()
    url = models.CharField(max_length=50)
    def  __str__(self):
        return self.titre