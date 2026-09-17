"""Apprendre les regions au lieu de les imposer.

L'effet regional des residus est-il une vraie structure de co-variation entre
communes, ou seulement la variance que la troncature de l'ACP a laissee de cote ?
Et si c'est une vraie structure, un clustering appris sur les donnees fait-il
mieux que les decoupages administratifs de la Confederation ?

Protocole honnete : les clusters sont appris sur les deux premiers tiers des
objets et evalues sur le tiers suivant. Sans ce partage, n'importe quel
clustering explique parfaitement les donnees qui l'ont engendre.

    .venv/bin/python var/clusters_residus.py
"""
import json
import os
import pathlib
import sqlite3
import sys

import django
import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "election.settings")
django.setup()

from sklearn.cluster import KMeans  # noqa: E402
from sklearn.decomposition import PCA  # noqa: E402
from sklearn.metrics import adjusted_rand_score  # noqa: E402

from scrutin.management.commands.backtest_ordre_depouillement import (  # noqa: E402
    ajuster,
    charger,
)

BASE = "var/backtest/snapshot.sqlite3"
CSV = "data/agvch_niveaux_2026-01-01.csv"
GEOJSON = "data/K4voge_20220501_gf.geojson"
DATE = "2026-06-14"


def residus(oui, non, bul, garde, indices, composantes):
    """Residu de chaque commune a chaque objet, modele ajuste sur tout le monde."""
    design = np.column_stack([composantes, np.ones(len(composantes))])
    sous_oui, sous_non = oui[garde][:, indices], non[garde][:, indices]
    exprimes = sous_oui + sous_non
    p = sous_oui / exprimes
    poids = np.nan_to_num(bul[garde][:, indices], nan=0.0)
    poids = np.where(poids > 0, poids, exprimes)
    sortie = np.empty_like(p)
    for j in range(p.shape[1]):
        sortie[:, j] = p[:, j] - design @ ajuster(design, p[:, j], poids[:, j])
    return sortie, poids


def part_expliquee(etiquettes, res, poids):
    """Part de variance des residus captee par les moyennes de groupe, par objet."""
    parts = []
    for j in range(res.shape[1]):
        r, w = res[:, j], poids[:, j]
        total = (w * r**2).sum()
        inter = 0.0
        for v in np.unique(etiquettes):
            m = etiquettes == v
            if m.sum() >= 3:
                inter += w[m].sum() * ((w[m] * r[m]).sum() / w[m].sum()) ** 2
        parts.append(inter / total if total > 0 else np.nan)
    return np.nanmedian(parts)


def centroides(ofs_par_commune):
    d = json.load(open(GEOJSON))
    coords = {}
    for f in d["features"]:
        geo = f["geometry"]
        morceaux = geo["coordinates"] if geo["type"] == "Polygon" else \
            [c for poly in geo["coordinates"] for c in poly]
        points = np.array([p for anneau in morceaux for p in anneau])
        coords[f["properties"]["vogeId"]] = points.mean(axis=0)
    manquant = np.array([np.nan, np.nan])
    return np.array([coords.get(int(o), manquant) if not pd.isna(o) else manquant
                     for o in ofs_par_commune])


def main():
    sujets, communes, oui, non, elec, bul = charger(BASE)
    anterieurs = [j for j, s in enumerate(sujets) if s[2] < DATE]
    coupe = int(len(anterieurs) * 2 / 3)
    train, test = anterieurs[:coupe], anterieurs[coupe:]
    print(f"{len(anterieurs)} objets avant {DATE} : {len(train)} pour apprendre, "
          f"{len(test)} pour evaluer\n")

    sous_oui, sous_non = oui[:, anterieurs], non[:, anterieurs]
    garde = ~np.isnan(sous_oui).any(axis=1) & ~np.isnan(sous_non).any(axis=1)
    matrice = sous_oui[garde] / (sous_oui[garde] + sous_non[garde])
    print(f"{garde.sum()} communes a l'historique complet\n")

    conn = sqlite3.connect(f"file:{BASE}?mode=ro&immutable=1", uri=True)
    infos = dict((r[0], (r[1], r[2], r[3])) for r in conn.execute(
        "select id, numero_ofs, canton_id, district_id from scrutin_commune"))
    conn.close()
    ids = [cid for cid, _ in communes]
    ofs = np.array([infos.get(i, (np.nan,) * 3)[0] for i in ids])[garde]
    canton = np.array([infos.get(i, (np.nan,) * 3)[1] for i in ids])[garde]
    district = np.array([infos.get(i, (np.nan,) * 3)[2] for i in ids])[garde]
    table = pd.read_csv(CSV).set_index("BfsCode")
    bassin = np.array([table["GBAE2018"].get(o, -1) for o in ofs])

    # --- 1. l'effet regional survit-il a plus de composantes ? --------------
    print("1. L'effet canton n'est-il que de la variance ACP tronquee ?\n")
    print(f"{'composantes':>12} {'var. ACP retenue':>17} {'part canton':>13} "
          f"{'part district':>14}")
    stock = {}
    for p in (6, 12, 20, 30, 50):
        acp = PCA(n_components=p)
        comp = acp.fit_transform(matrice)
        res_tr, poids_tr = residus(oui, non, bul, garde, train, comp)
        res_te, poids_te = residus(oui, non, bul, garde, test, comp)
        stock[p] = (comp, res_tr, poids_tr, res_te, poids_te)
        print(f"{p:>12} {acp.explained_variance_ratio_.sum():>16.1%} "
              f"{part_expliquee(canton, res_te, poids_te):>12.1%} "
              f"{part_expliquee(district, res_te, poids_te):>13.1%}")

    # --- 2. clustering appris contre decoupages imposes ---------------------
    for p in (6, 20):
        comp, res_tr, poids_tr, res_te, poids_te = stock[p]
        print(f"\n2. Clustering appris sur les residus — modele a {p} composantes")
        # On travaille sur les residus normalises par commune : c'est la
        # co-variation qui nous interesse, pas l'amplitude.
        norme = res_tr / np.maximum(res_tr.std(axis=1, keepdims=True), 1e-9)
        facteurs = PCA(n_components=12).fit_transform(norme)

        print(f"\n{'methode':>26} {'groupes':>8} {'part expliquee':>15} "
              f"{'au hasard':>10} {'ARI canton':>11}")
        rng = np.random.default_rng(0)
        reference = [("canton (impose)", canton), ("district (impose)", district),
                     ("bassin d'emploi (impose)", bassin)]
        for nom, etiquettes in reference:
            k = len(np.unique(etiquettes))
            hasard = part_expliquee(rng.permutation(etiquettes), res_te, poids_te)
            print(f"{nom:>26} {k:>8} {part_expliquee(etiquettes, res_te, poids_te):>14.1%} "
                  f"{hasard:>9.1%} {adjusted_rand_score(canton, etiquettes):>11.2f}")
        for k in (7, 13, 26, 60, 144):
            etiquettes = KMeans(n_clusters=k, n_init=10, random_state=0).fit_predict(facteurs)
            hasard = part_expliquee(rng.permutation(etiquettes), res_te, poids_te)
            print(f"{'KMeans sur residus':>26} {k:>8} "
                  f"{part_expliquee(etiquettes, res_te, poids_te):>14.1%} "
                  f"{hasard:>9.1%} {adjusted_rand_score(canton, etiquettes):>11.2f}")

    # --- 3. les facteurs de residus sont-ils geographiques ? ----------------
    comp, res_tr, poids_tr, res_te, poids_te = stock[6]
    norme = res_tr / np.maximum(res_tr.std(axis=1, keepdims=True), 1e-9)
    acp_res = PCA(n_components=12).fit(norme)
    facteurs = acp_res.transform(norme)
    print("\n3. Les facteurs de co-variation sont-ils geographiques ?")
    print(f"   variance des residus portee par les 12 facteurs : "
          f"{acp_res.explained_variance_ratio_.sum():.1%}")
    print(f"\n{'facteur':>8} {'var.':>7} {'R2 canton':>10} {'R2 district':>12}")
    for f in range(6):
        y = facteurs[:, f]
        r2 = []
        for etiquettes in (canton, district):
            moyennes = np.array([y[etiquettes == v].mean() for v in etiquettes])
            r2.append(1 - ((y - moyennes) ** 2).sum() / ((y - y.mean()) ** 2).sum())
        print(f"{f + 1:>8} {acp_res.explained_variance_ratio_[f]:>6.1%} "
              f"{r2[0]:>10.2f} {r2[1]:>12.2f}")

    # --- 4. portee spatiale ------------------------------------------------
    xy = centroides(ofs)
    ok = ~np.isnan(xy).any(axis=1)
    echantillon = np.where(ok)[0][:: max(1, ok.sum() // 400)]
    pts = xy[echantillon]
    # degres -> km, projection locale suffisante a l'echelle de la Suisse
    km = np.column_stack([pts[:, 0] * 111 * np.cos(np.radians(pts[:, 1])),
                          pts[:, 1] * 111])
    r = norme[echantillon]
    correlations = np.corrcoef(r)
    distances = np.sqrt(((km[:, None, :] - km[None, :, :]) ** 2).sum(-1))
    triangle = np.triu_indices(len(echantillon), 1)
    d, c = distances[triangle], correlations[triangle]
    print("\n4. Portee spatiale de la co-variation des residus")
    print(f"{'distance (km)':>16} {'paires':>8} {'correlation':>12}")
    bornes = [0, 5, 10, 20, 40, 80, 150, 300]
    for a, b in zip(bornes[:-1], bornes[1:]):
        m = (d >= a) & (d < b)
        if m.sum() > 20:
            print(f"{f'{a}-{b}':>16} {m.sum():>8} {c[m].mean():>12.3f}")


main()
