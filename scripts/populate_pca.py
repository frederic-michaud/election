from scrutin.models import Commune, Canton, District, Voix, SujetVote
from pca.models import PCAResult
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
import scipy.cluster.hierarchy as hier
import sys
sys.setrecursionlimit(5000)
print(sys.getrecursionlimit())
#ci-dessous ajouté par Laurence en test
from sklearn.cluster import AgglomerativeClustering
#import scipy.sklearn.cluster
#from scipy.sklearn.cluster import AgglomerativeClustering
def get_percentage(voix):
    return voix.nombre_oui/(voix.nombre_oui + voix.nombre_non)

def compute_pca():
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
    X_reduced = PCA(n_components=2).fit_transform(percentage_oui_all_commune)
    return valid_communes, X_reduced

def run():
    valid_communes, X = compute_pca()
    entries = []
    for commune, (x1, x2) in zip(valid_communes, X):
        entries.append(PCAResult(commune = commune, coordinate_1 = x1, coordinate_2 = x2))
    PCAResult.objects.bulk_create(entries)


    # df = pd.DataFrame(percentage_oui_all_commune, index = commune_names, columns = sujets)
    # plot = sns.clustermap(df)
    # plt.savefig('voir.pdf', bbox_inches='tight')
    # X = np.array(percentage_oui_all_commune, dtype=float)
    # Z = hier.linkage(X, method = 'ward')
    # commune_a_garder = ['Bussigny', 'Lausanne', 'Bern', 'Zürich', 'Basel', 'Altdorf (UR)', 'Romainmôtier-Envy','Lugano', 'Hindelbank', 'Kirchdorf (BE)']
    # commune_names_main = [commune if commune in commune_a_garder else '.' for commune in commune_names]
    # hier.dendrogram(Z, labels= commune_names_main, orientation='right')

    # fig = plot.get_figure()
    # plt.savefig("out.pdf", bbox_inches='tight')
