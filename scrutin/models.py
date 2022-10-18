from django.db import models


class SujetVote(models.Model):
    nom = models.CharField(max_length=500)
    sujet_id = models.IntegerField(default=1)
    date = models.DateField()
    def  __str__(self):
        return self.nom
    def get_unique_sujet_vote(nom):
        sujet_votes = SujetVote.objects.filter(nom=nom)
        if len(sujet_votes) == 0:
            raise Exception(f'There is no vote subject {nom}')
        if len(sujet_votes) > 1:
            raise Exception(f'There are more than one vote subject named {nom}')
        return sujet_votes[0]


class Canton(models.Model):
    nom = models.CharField(max_length=30)
    abreviation = models.CharField(max_length=2)
    def  __str__(self):
        return  self.nom

    def get_unique_canton_by_abreviation(abr):
        cantons = Canton.objects.filter(abreviation=abr)
        if len(cantons) == 0:
            raise Exception(f'There is no canton abreviated {abr}')
        if len(cantons) > 1:
            raise Exception(f'There are more than one canton abreviated {abr}')
        return cantons[0]

class District(models.Model):
    nom = models.CharField(max_length=50)
    numero_ofs = models.IntegerField()
    canton = models.ForeignKey(Canton, on_delete=models.CASCADE)
    def  __str__(self):
        return  self.nom


    def get_unique_district_by_name(nom):
        districts = District.objects.filter(nom=nom)
        if len(districts) == 0:
            raise Exception(f'There is no district named {nom}')
        if len(districts) > 1:
            raise Exception(f'There are more than one district named {nom}')
        return districts[0]

class Commune(models.Model):
    nom = models.CharField(max_length=50)
    numero_ofs = models.IntegerField(default=0, db_index=True)
    est_valide = models.BooleanField(default=True)
    langue = models.CharField(max_length=20,null=True)
    degre_urbanisation = models.CharField(max_length=50,null=True)
    district = models.ForeignKey(District, on_delete=models.CASCADE, default=0)
    canton = models.ForeignKey(Canton, on_delete=models.CASCADE, default=0)
    nb_voix = models.IntegerField(default=0)
    def  __str__(self):
        return  self.nom

    def get_unique_commune_by_name(nom):
        communes = Commune.objects.filter(nom=nom)
        if len(communes) == 0:
            raise Exception(f'There is no commune named {nom}')
        if len(communes) > 1:
            raise Exception(f'There are more than one commune named {nom}')
        return communes[0]

    def get_unique_commune_by_ofs(numero_ofs):
        communes = Commune.objects.filter(numero_ofs=numero_ofs)
        if len(communes) == 0:
            raise Exception(f'There is no commune with numero ofs {numero_ofs}')
        if len(communes) > 1:
            raise Exception(f'There are more than one commune with numero ofs {numero_ofs}')
        return communes[0]

    def set_voix(self):
        self.nb_voix = self.get_last_nb_electeur_slow()
        self.save()

    def get_last_nb_electeur_slow(self):
        voix = Voix.objects.filter(commune = self)
        list(voix).sort(key = lambda obj: obj.sujet_vote.date)
        if len(voix) > 0 :
            return voix[0].electeurs_inscrits
        import warnings
        warnings.warn(f"Nb electeur not found for {self}")
        return 0


class Voix(models.Model):
    sujet_vote = models.ForeignKey(SujetVote, default=1, on_delete=models.CASCADE)
    commune = models.ForeignKey(Commune, on_delete=models.CASCADE)
    nombre_oui = models.IntegerField()
    nombre_non = models.IntegerField()
    electeurs_inscrits = models.IntegerField()
    bulletins_rentres = models.IntegerField()
    def __str__(self):
        return str(self.commune) + " " + str(self.sujet_vote)


class ScrutinEnCours(models.Model):
    sujet_vote = models.ForeignKey(SujetVote, on_delete=models.CASCADE)
    commune = models.ForeignKey(Commune, on_delete=models.CASCADE)
    nombre_oui = models.IntegerField(null=True)
    nombre_non = models.IntegerField(null=True)
    electeurs_inscrits = models.IntegerField(null=True)
    bulletins_rentres = models.IntegerField(null=True)
    electeur_election_precedente = models.IntegerField()
    comptabilise = models.BooleanField(default=False)
    def __str__(self):
        return str(self.commune) + " " + str(self.sujet_vote)
    def get_pourcentage_oui(self):
        return self.nombre_oui/(self.nombre_oui + self.nombre_non)
    def get_real_participation(self):
        return (self.nombre_oui + self.nombre_non)/self.electeurs_inscrits



class Extrapolation(models.Model):
    sujet_vote = models.ForeignKey(SujetVote, on_delete=models.CASCADE)
    pourcentage_oui_connu = models.FloatField()
    pourcentage_oui_extrapole = models.FloatField()
    avance = models.FloatField()
    moment_creation = models.DateTimeField(auto_now_add=True)

def get_percentage(voix):
    return voix.nombre_oui/(voix.nombre_oui + voix.nombre_non)

class ScrutinAPI:
    def getVotationMatrixWithMetaInfo():
        valid_communes = []
        percentage_oui_all_commune = []
        for commune in Commune.objects.all():
            voix = Voix.objects.filter(commune=commune)
            if len(voix) != 55:
                Warning(f"{commune} has only {len(voix)} and will be dropped from the PCA")
                continue
            valid_communes.append(commune)
            voixs = Voix.objects.filter(commune=commune).order_by('sujet_vote')
            percentage_oui = [get_percentage(voix) for voix in voixs]
            percentage_oui_all_commune.append(percentage_oui)
        sujets = [voix.sujet_vote.nom for voix in voixs]
        return (sujets, valid_communes), percentage_oui_all_commune

    def get_nb_inscrit():
        nb_inscrit_all_commune = []
        for commune in Commune.objects.all():
            voix = Voix.objects.filter(commune=commune)
            if len(voix) != 55:
                Warning(f"{commune} has only {len(voix)} and will be dropped from the result")
                continue
            voixs = Voix.objects.filter(commune=commune).order_by('sujet_vote')
            nb_inscrit_all_commune.append((commune.nom, [(voix.electeurs_inscrits, voix.sujet_vote.date) for voix in voixs]))
        return nb_inscrit_all_commune

    def get_percentage_oui_all_commune(sujet_id):
        scrutin_en_cours = ScrutinEnCours.objects.filter(sujet_vote_id = sujet_id).select_related('commune')
        return {scrutin.commune.numero_ofs: scrutin.get_pourcentage_oui() for scrutin in scrutin_en_cours}