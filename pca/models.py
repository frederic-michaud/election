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
    def get_component(self, nb_component):
        if nb_component > 6:
            raise Exception('Cannot currently return more than 6 components')
        return [self.coordinate_1, self.coordinate_2, self.coordinate_3, self.coordinate_4, self.coordinate_5,
                self.coordinate_6][0:nb_component]
