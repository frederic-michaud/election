from scrutin.models import Commune, Canton, District, Voix, SujetVote
import pandas as pd

def import_commune(path_commune):
    df_communes = pd.read_csv(path_commune, sep = ";")
    for commune in df_communes.itertuples():
        cantons = Canton.objects.filter(nom = commune.Canton)
        if len(cantons) == 0:
            canton = Canton(nom = commune.Canton, nb_communes = 1)
        elif len(cantons) == 1:
            canton = cantons[0]
            canton.nb_communes += 1
        else:
            raise Exception(f'There are more than one canton named {commune.Canton}')
        canton.save()
        districts = District.objects.filter(nom = commune.district)
        if len(districts) == 0:
            district = District(nom=commune.district, numero_ofs=commune.numero_ofs, canton=canton)
        elif len(districts) == 1:
            district = districts[0]
        else:
            raise Exception(f'There are more than one district named {commune.district}')
        district.save()
        commune_db = Commune(nom = commune.nom, numero_ofs = commune.numero_ofs, canton = canton, district = district)
        commune_db.save()

def import_votation(path_votation):
    df_full = pd.read_csv(path_votation, sep = ";")
    df_full.fillna(method='ffill', inplace=True)
    def is_commune(nom_commune):
        #    if type(nom_commune) == float:
        #        return False
        if nom_commune[0:6] != "......":
            return False
        if nom_commune in ['......Blatten', '......Jaberg', '......Rüti bei Lyssach']:
            return False
        return True
    def has_electeur(inscrit):
        if inscrit == '...':
            return False
        return True
    def clean_commune_name(nom_commune):
        return nom_commune[6:]
    def clean_electeur(nb_electeur_string):
        try:
            nb_electeur = int(nb_electeur_string[:-3])
        except:
            return 0
        return nb_electeur
    def clean_percentage(percent_string):
        try:
            percent = float(percent_string.replace(',', '.'))
        except:
            return 0
        return percent
    def clean_oui_non(oui_non_string):
        return int(oui_non_string[:-3])

    df_commune = df_full[df_full['commune'].apply(is_commune)]
    df_commune = df_commune[df_commune['Electeurs inscrits'].apply(has_electeur)]
    df_commune['commune'] = df_commune['commune'].apply(clean_commune_name)
    df_commune['Oui'] = df_commune['Oui'].apply(clean_oui_non)
    df_commune['Non'] = df_commune['Non'].apply(clean_oui_non)
    df_commune['Electeurs inscrits'] = df_commune['Electeurs inscrits'].apply(clean_electeur)
    df_commune['Participation en %'] = df_commune['Participation en %'].apply(clean_percentage)
    df_commune['Oui en %'] = df_commune['Oui en %'].apply(clean_percentage)
    for commune_voix in df_commune.itertuples():
        sujet_votes = SujetVote.objects.filter(sujet_id=commune_voix.sujet_id)
        if len(sujet_votes) == 0:
            sujet_vote = SujetVote(id=commune_voix.sujet_id, nom = commune_voix.sujet)
        elif len(sujet_votes) == 1:
            sujet_vote = sujet_votes[0]
        else:
            raise Exception(f'There are more than one canton named {commune.Canton}')
        sujet_vote.save()
        communes = Commune.objects.filter(nom = commune_voix.commune)
        if len(communes) == 0:
            raise Exception(f'commune not found: {commune_voix.commune}')
        elif len(communes) > 1:
            raise Exception(f'More than one commune with name: {commune_voix.commune}')
        commune = communes[0]
        commune.save()
        voix = Voix(commune = commune,
                    sujet_vote = sujet_vote,
                    nombre_oui = commune_voix.Oui,
                    nombre_non = commune_voix.Non)
        voix.save()

def run():
    import_commune("../data/communes/Communes_actuelles.csv")
    import_votation("../data/donnee_federale_v2.csv")
    #print(df_communes.head())