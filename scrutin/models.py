import warnings

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
        voix = ResultatCommunalHistorique.objects.filter(commune = self).order_by('-sujet_vote__date').first()
        if voix is not None:
            return voix.electeurs_inscrits
        warnings.warn(f"Nb electeur not found for {self}")
        return 0


class ResultatCommunalHistorique(models.Model):
    sujet_vote = models.ForeignKey(SujetVote, default=1, on_delete=models.CASCADE)
    commune = models.ForeignKey(Commune, on_delete=models.CASCADE)
    nombre_oui = models.IntegerField()
    nombre_non = models.IntegerField()
    electeurs_inscrits = models.IntegerField()
    bulletins_rentres = models.IntegerField()
    def __str__(self):
        return str(self.commune) + " " + str(self.sujet_vote)


class ResultatCommunalEnCours(models.Model):
    sujet_vote = models.ForeignKey(SujetVote, on_delete=models.CASCADE)
    commune = models.ForeignKey(Commune, on_delete=models.CASCADE)
    nombre_oui = models.IntegerField(null=True)
    nombre_non = models.IntegerField(null=True)
    electeurs_inscrits = models.IntegerField(null=True)
    bulletins_rentres = models.IntegerField(null=True)
    electeur_election_precedente = models.IntegerField()
    comptabilise = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["commune", "sujet_vote"],
                                    name="une_ligne_par_commune_et_objet"),
        ]

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


def nb_sujets_historiques():
    """Nombre d'objets de votation présents dans l'historique.

    Remplace le « 55 » qui était codé en dur : il fallait le mettre à jour à
    chaque votation ajoutée, faute de quoi toutes les communes étaient écartées
    de l'ACP sans que rien ne le signale.
    """
    return ResultatCommunalHistorique.objects.values('sujet_vote').distinct().count()


def resultats_historiques_par_commune():
    """Tout l'historique, groupé par commune, en une seule requête.

    Chaque liste est ordonnée par objet de votation : c'est ce qui garantit que
    les colonnes de la matrice ACP désignent le même objet d'une commune à
    l'autre.
    """
    resultats = {}
    for voix in ResultatCommunalHistorique.objects.select_related('sujet_vote').order_by('sujet_vote'):
        resultats.setdefault(voix.commune_id, []).append(voix)
    return resultats


class ScrutinAPI:
    def getVotationMatrixWithMetaInfo():
        attendu = nb_sujets_historiques()
        resultats = resultats_historiques_par_commune()
        valid_communes = []
        percentage_oui_all_commune = []
        sujets = []
        for commune in Commune.objects.all():
            voixs = resultats.get(commune.id, [])
            if len(voixs) != attendu:
                warnings.warn(f"{commune} has only {len(voixs)} of {attendu} historical "
                              "results and will be dropped from the PCA")
                continue
            valid_communes.append(commune)
            percentage_oui = [get_percentage(voix) for voix in voixs]
            percentage_oui_all_commune.append(percentage_oui)
            if not sujets:
                sujets = [voix.sujet_vote.nom for voix in voixs]
        return (sujets, valid_communes), percentage_oui_all_commune

    def get_nb_inscrit():
        attendu = nb_sujets_historiques()
        resultats = resultats_historiques_par_commune()
        nb_inscrit_all_commune = []
        for commune in Commune.objects.all():
            voixs = resultats.get(commune.id, [])
            if len(voixs) != attendu:
                warnings.warn(f"{commune} has only {len(voixs)} of {attendu} historical "
                              "results and will be dropped from the result")
                continue
            nb_inscrit_all_commune.append((commune.nom, [(voix.electeurs_inscrits, voix.sujet_vote.date) for voix in voixs]))
        return nb_inscrit_all_commune
