from scrutin.models import ScrutinAPI
from pca.models import PCAResult
from sklearn.decomposition import PCA

#import numpy as np
#import matplotlib.pyplot as plt
#import scipy.cluster.hierarchy as hier
#import sys
#sys.setrecursionlimit(5000)

def compute_pca():
    (sujets, communes), X = ScrutinAPI.getVotationMatrixWithMetaInfo()
    X_reduced = PCA(n_components=6).fit_transform(X)
    return communes, X_reduced

def run():
    valid_communes, X = compute_pca()
    entries = []
    for commune, (x1, x2, x3, x4, x5, x6) in zip(valid_communes, X):
        entries.append(PCAResult(commune = commune,
                                 coordinate_1 = x1,
                                 coordinate_2 = x2,
                                 coordinate_3 = x3,
                                 coordinate_4 = x4,
                                 coordinate_5 = x5,
                                 coordinate_6 = x6))
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
