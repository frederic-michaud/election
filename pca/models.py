from django.db import models
from scrutin.models import Commune, Canton, District, Voix, SujetVote


class PCAResult(models.Model):
    commune = models.ForeignKey(Commune, on_delete=models.CASCADE)
    coordinate_1 = models.FloatField()
    coordinate_2 = models.FloatField()
    def  __str__(self):
        return str(self.commune)