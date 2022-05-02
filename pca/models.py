from django.db import models
from scrutin.models import Commune


class PCAResult(models.Model):
    commune = models.ForeignKey(Commune, on_delete=models.CASCADE)
    coordinate_1 = models.FloatField()
    coordinate_2 = models.FloatField()
    coordinate_3 = models.FloatField()
    coordinate_4 = models.FloatField()
    coordinate_5 = models.FloatField()
    coordinate_6 = models.FloatField()
    def  __str__(self):
        return str(self.commune)