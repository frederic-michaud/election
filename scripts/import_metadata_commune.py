from scrutin.models import Commune
import pandas as pd
import numpy as np



def  import_commune(path_commune):
    #load data

    df_meta_donnee_commune = pd.read_csv('../data/communes/commune_meta_info.txt')
    for row_commune in df_meta_donnee_commune.itertuples():
        try:
            commune_db = Commune.get_unique_commune_by_ofs(row_commune.CODE_OFS)
            commune_db.langue = row_commune.HR_SPRGEB2016_Name_fr
            commune_db.degre_urbanisation = row_commune.HR_GDETYP2012_L1_Name_fr
            commune_db.save()
        except:
            print(f'unable to find info for {row_commune.Name_fr} with numero OFS {row_commune.CODE_OFS}')




def run():
    import_commune("../data/communes/commune_meta_info.txt")