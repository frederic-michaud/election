from scrutin.models import Commune, Canton, District, Voix, SujetVote
import pandas as pd
import numpy as np

fusions = {"Galmiz": "Murten", "Gempenach": "Murten", "Clavaleyres": "Murten",
           "Bözen": "Böztal", "Effingen": "Böztal", "Elfingen": "Böztal", "Hornussen": "Böztal",
           "Melano": "Val Mara", "Maroggia": "Val Mara", "Rovio": "Val Mara",
           "Wislikofen": "Zurzach", "Baldingen": "Zurzach", "Böbikon": "Zurzach", "Kaiserstuhl": "Zurzach",
           "Rümikon": "Zurzach", "Rietheim": "Zurzach", "Rekingen (AG)": "Zurzach", "Bad Zurzach": "Zurzach",
           "Essertes": "Oron",
           "Blonay": "Blonay - Saint-Légier", "Saint-Légier-La Chiésaz": "Blonay - Saint-Légier"
           }

def import_votation(path_votation):
    df_full = pd.read_csv(path_votation, sep = ";")
    df_full.fillna(method='ffill', inplace=True)
    def is_commune(nom_commune):
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
    df_commune = df_commune[df_commune['Electeurs_inscrits'].apply(has_electeur)]
    df_commune['commune'] = df_commune['commune'].apply(clean_commune_name)
    df_commune['Oui'] = df_commune['Oui'].apply(clean_oui_non)
    df_commune['Non'] = df_commune['Non'].apply(clean_oui_non)
    df_commune['Bulletins_rentres'] = df_commune['Bulletins_rentres'].apply(clean_oui_non)
    df_commune['Electeurs_inscrits'] = df_commune['Electeurs_inscrits'].apply(clean_electeur)
    df_commune['Participation en %'] = df_commune['Participation en %'].apply(clean_percentage)
    df_commune['Oui en %'] = df_commune['Oui en %'].apply(clean_percentage)
    commune_fusionnee_a_ajouter = []
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
            if "Ausland" in commune_voix.commune or "étranger" in commune_voix.commune or "estero" in commune_voix.commune:
                add_foreigner(commune_voix, sujet_vote)
                continue
            if commune_voix.commune in list(fusions.keys()):
                commune_fusionnee_a_ajouter.append((fusions[commune_voix.commune], commune_voix))
                continue
            raise Exception(f'commune not found: {commune_voix.commune}')
        elif len(communes) > 1:
            raise Exception(f'More than one commune with name: {commune_voix.commune}')
        commune = communes[0]
        commune.save()
        voix = Voix(commune = commune,
                    sujet_vote = sujet_vote,
                    nombre_oui = commune_voix.Oui,
                    nombre_non = commune_voix.Non,
                    electeurs_inscrits = commune_voix.Electeurs_inscrits,
                    bulletins_rentres = commune_voix.Bulletins_rentres
                    )
        voix.save()
    add_fusion(commune_fusionnee_a_ajouter)

def add_fusion(commune_fusionnee_a_ajouter):
    for commune_name, commune_voix in commune_fusionnee_a_ajouter:
        commune = Commune.get_unique_commune_by_name(commune_name)
        sujet_vote = SujetVote.get_unique_sujet_vote(commune_voix.sujet)
        voixs = Voix.objects.filter(commune = commune, sujet_vote = sujet_vote)
        if len(voixs) == 0:
            voix = Voix(commune=commune,
                        sujet_vote=sujet_vote,
                        nombre_oui=0,
                        nombre_non=0,
                        electeurs_inscrits=0,
                        bulletins_rentres=0)
        elif len(voixs) == 1:
            voix = voixs[0]
        else:
            raise Exception(f'problem when looking for a voixs with {commune} and {sujet_vote}')
        voix.nombre_oui += commune_voix.Oui
        voix.nombre_non += commune_voix.Non
        voix.electeurs_inscrits += commune_voix.Electeurs_inscrits
        voix.bulletins_rentres += commune_voix.Bulletins_rentres
        voix.save()

def add_foreigner(commune_voix, sujet_vote):
    def get_canton_from_foreign(name):
        return name[:2]
    canton_abrev = get_canton_from_foreign(commune_voix.commune)
    canton = Canton.get_unique_canton_by_abreviation(canton_abrev)
    canton.save()
    name_district = f'{canton_abrev}-étranger'
    districts = District.objects.filter(nom=name_district)
    if len(districts) == 0:
        district = District(nom=name_district, numero_ofs=0, canton=canton)
    elif len(districts) == 1:
        district = districts[0]
    else:
        raise Exception(f'There are more than one district named {name_district}')
    district.save()
    name_commune = name_district
    communes = Commune.objects.filter(nom=name_commune)
    if len(communes) == 0:
        commune = Commune(nom=name_commune, numero_ofs=0, district = district, canton=canton)
    elif len(districts) == 1:
        commune = communes[0]
    else:
        raise Exception(f'There are more than one commune named {name_commune}')
    commune.save()
    voix = Voix(commune=commune,
                sujet_vote=sujet_vote,
                nombre_oui=commune_voix.Oui,
                nombre_non=commune_voix.Non,
                electeurs_inscrits=commune_voix.Electeurs_inscrits,
                bulletins_rentres=commune_voix.Bulletins_rentres
                )
    voix.save()

def run():
    SujetVote.objects.all().delete()
    import_votation("../data/donnee_federale_v3.txt")