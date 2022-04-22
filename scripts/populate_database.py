from scrutin.models import Commune, Canton, District, Voix, SujetVote
import pandas as pd

canton_par_abrev = {"ZH": "Zürich", "BE": "Berne", "LU": "Lucerne", "UR": "Uri", "SZ": "Schwytz", "OW": "Obwald",
                    "NW": "Nidwald", "GL": "Glaris", "ZG": "Zoug", "FR": "Fribourg", "SO": "Soleure",
                    "BS": "Bâle-Ville", "BL": "Bâle-Campagne", "SH": "Schaffhouse",
                    "AR": "Appenzell Rhodes-Extérieures", "AI": "Appenzell Rhodes-Intérieures", "SG": "Saint-Gall",
                    "GR": "Grisons", "AG": "Argovie", "TG": "Thurgovie", "TI": "Tessin", "VD": "Vaud", "VS": "Valais",
                    "NE": "Neuchâtel", "GE": "Genève", "JU": "Jura"}

def import_commune(path_commune):
    df_communes = pd.read_csv(path_commune, sep = ";")
    for commune in df_communes.itertuples():
        cantons = Canton.objects.filter(abreviation = commune.Canton)
        if len(cantons) == 0:
            canton = Canton(abreviation = commune.Canton,
                            nom = canton_par_abrev[commune.Canton])
        elif len(cantons) == 1:
            canton = cantons[0]
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
        fusions = {"Galmiz":"Murten", "Gempenach":"Murten", "Clavaleyres":"Murten",
                   "Bözen":"Böztal", "Effingen":"Böztal", "Elfingen":"Böztal", "Hornussen":"Böztal",
                   "Melano":"Val Mara", "Maroggia":"Val Mara", "Rovio":"Val Mara",
                   "Wislikofen":"Zurzach","Baldingen":"Zurzach","Böbikon":"Zurzach","Kaiserstuhl":"Zurzach","Rümikon":"Zurzach","Rietheim":"Zurzach","Rekingen (AG)":"Zurzach","Bad Zurzach":"Zurzach",
                   "Essertes":"Oron",
                   "Blonay":"Blonay - Saint-Légier", "Saint-Légier-La Chiésaz":"Blonay - Saint-Légier"
                   }

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
    for commune_name, commune_voix in commune_fusionnee_a_ajouter:
        print(commune_name)
        print(commune_voix)
        communes = Commune.objects.filter(nom = commune_name)
        sujet_votes = SujetVote.objects.filter(nom = commune_voix.sujet)
        if len(communes) != 1 or len(sujet_votes) != 1:
            raise Exception('problem when looking for commune or subject')
        voixs = Voix.objects.filter(commune = communes[0], sujet_vote = sujet_votes[0])
        if len(voixs) == 0:
            voix = Voix(commune=communes[0],
                        sujet_vote=sujet_votes[0],
                        nombre_oui=0,
                        nombre_non=0,
                        electeurs_inscrits=0,
                        bulletins_rentres=0
                        )
        elif len(voixs) == 1:
            voix = voixs[0]
        else:
            raise Exception('problem when looking for a voixs')
        voix.nombre_oui += commune_voix.Oui
        voix.nombre_non += commune_voix.Non
        voix.electeurs_inscrits += commune_voix.Electeurs_inscrits
        voix.bulletins_rentres += commune_voix.Bulletins_rentres
        voix.save()



def add_foreigner(commune_voix, sujet_vote):
    def get_canton_from_foreign(name):
        return name[:2]
    canton_abrev = get_canton_from_foreign(commune_voix.commune)
    cantons = Canton.objects.filter(abreviation=canton_abrev)
    if len(cantons) == 0:
        raise Exception(f'There are no canton abreviated {canton_abrev}')
    elif len(cantons) == 1:
        canton = cantons[0]
    else:
        raise Exception(f'There are more than one canton named {canton_abrev}')
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
    import_commune("../data/communes/Communes_actuelles.csv")
    import_votation("../data/donnee_federale_v3.txt")
    #print(df_communes.head())