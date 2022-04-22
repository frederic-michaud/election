from scrutin.models import Commune, Canton, District, Voix, SujetVote
import pandas as pd
import numpy as np

canton_par_abrev = {"ZH": "Zürich", "BE": "Berne", "LU": "Lucerne", "UR": "Uri", "SZ": "Schwytz", "OW": "Obwald",
                    "NW": "Nidwald", "GL": "Glaris", "ZG": "Zoug", "FR": "Fribourg", "SO": "Soleure",
                    "BS": "Bâle-Ville", "BL": "Bâle-Campagne", "SH": "Schaffhouse",
                    "AR": "Appenzell Rhodes-Extérieures", "AI": "Appenzell Rhodes-Intérieures", "SG": "Saint-Gall",
                    "GR": "Grisons", "AG": "Argovie", "TG": "Thurgovie", "TI": "Tessin", "VD": "Vaud", "VS": "Valais",
                    "NE": "Neuchâtel", "GE": "Genève", "JU": "Jura"}

def create_cantons(list_of_canton):
    Canton.objects.all().delete()
    for canton in list_of_canton:
        canton = Canton(abreviation=canton,
                        nom=canton_par_abrev[canton])
        canton.save()

def create_districts(districts_per_canton):
    District.objects.all().delete()
    for canton, districts_info in districts_per_canton.items():
        canton = get_unique_canton_by_abreviation(canton)
        for district_info in districts_info:
            district = District(nom = district_info["nom"],
                                numero_ofs = district_info["numero"],
                                canton = canton)
            district.save()

def get_unique_canton_by_abreviation(abr):
    cantons = Canton.objects.filter(abreviation=abr)
    if len(cantons) == 0:
        raise Exception(f'There is no canton abreviated {abr}')
    if len(cantons) > 1:
        raise Exception(f'There are more than one canton abreviated {abr}')
    return cantons[0]

def get_unique_district_by_name(nom):
    districts = District.objects.filter(nom=nom)
    if len(districts) == 0:
        raise Exception(f'There is no district named {nom}')
    if len(districts) > 1:
        raise Exception(f'There are more than one district named {nom}')
    return districts[0]

def  import_commune(path_commune):
    #load data
    df_communes = pd.read_csv(path_commune, sep = ";")
    #import canton
    create_cantons(np.unique(df_communes['canton']))
    # import district
    district_by_canton = {}
    for district_info_tuple, _ in df_communes.groupby(['district', 'district_id', 'canton']):
        district_info = {"nom": district_info_tuple[0],"numero": district_info_tuple[1]}
        canton_name = district_info_tuple[2]
        if canton_name in district_by_canton.keys():
            district_by_canton[canton_name].append(district_info)
        else:
            district_by_canton[canton_name] = [district_info]
    create_districts(district_by_canton)
    # import commune
    for commune in df_communes.itertuples():
        canton = get_unique_canton_by_abreviation(commune.canton)
        district = get_unique_district_by_name(commune.district)
        commune_db = Commune(nom=commune.nom,
                             numero_ofs=commune.numero_ofs,
                             canton=canton,
                             district=district)
        commune_db.save()



def run():
    import_commune("../data/communes/Communes_actuelles.csv")