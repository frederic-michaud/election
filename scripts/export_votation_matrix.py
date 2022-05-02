from scrutin.models import ScrutinAPI
import pandas as pd

def run():
    (sujets, communes), X = ScrutinAPI.getVotationMatrixWithMetaInfo()
    df_export = pd.DataFrame(X, index=communes, columns=sujets)
    df_export.to_csv('votation_matrix.csv')

