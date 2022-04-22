from django.db import models


class SujetVote(models.Model):
    nom = models.CharField(max_length=500)
    sujet_id = models.IntegerField(default=1)
    def  __str__(self):
        return self.nom
    #date = models.DateField()

class Canton(models.Model):
    nom = models.CharField(max_length=30)
    abreviation = models.CharField(max_length=2)
    def  __str__(self):
        return  self.nom

class District(models.Model):
    nom = models.CharField(max_length=50)
    numero_ofs = models.IntegerField()
    canton = models.ForeignKey(Canton, on_delete=models.CASCADE)
    def  __str__(self):
        return  self.nom


class Commune(models.Model):
    nom = models.CharField(max_length=50)
    numero_ofs = models.IntegerField(default=0)
    est_valide = models.BooleanField(default=True)
    district = models.ForeignKey(District, on_delete=models.CASCADE, default=0)
    canton = models.ForeignKey(Canton, on_delete=models.CASCADE, default=0)
    def  __str__(self):
        return  self.nom


class Voix(models.Model):
    sujet_vote = models.ForeignKey(SujetVote, default=1, on_delete=models.CASCADE)
    commune = models.ForeignKey(Commune, on_delete=models.CASCADE)
    nombre_oui = models.IntegerField()
    nombre_non = models.IntegerField()
    electeurs_inscrits = models.IntegerField()
    bulletins_rentres = models.IntegerField()
    def __str__(self):
        return str(self.commune) + " " + str(self.sujet_vote)