from django.db import models

from scrutin.models import Commune

# Axes calculés par populate_pca et utilisés par l'extrapolation (doc/backtest.md).
NB_AXES = 16


class PCAResult(models.Model):
    commune = models.ForeignKey(Commune, on_delete=models.CASCADE)
    coordonnees = models.JSONField()

    def __str__(self):
        return str(self.commune)

    def get_component(self, nb_component):
        if nb_component > len(self.coordonnees):
            raise ValueError(f"{self.commune} n'a que {len(self.coordonnees)} axes : "
                             "relancer populate_pca")
        return self.coordonnees[:nb_component]
