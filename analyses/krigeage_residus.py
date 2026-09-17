"""Corriger les communes manquantes par les residus de leurs voisines.

Idee de Frederic : plutot que d'ajouter des composantes a l'ACP — qui supposent
que l'effet regional existait deja dans le passe, et qui coutent des degres de
liberte — on estime le decalage regional *le jour meme*, a partir des residus
des communes voisines deja depouillees.

C'est de la regression-krigeage. La structure de covariance vient du
variogramme mesure sur l'historique (correlation 0.31 a moins de 5 km,
nulle au-dela de 40 km), donc elle ne consomme aucun parametre du fit du jour.

    .venv/bin/python var/krigeage_residus.py [avance] [tirages]
"""
import json
import os
import pathlib
import sqlite3
import sys

import django
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "election.settings")
django.setup()

from scrutin.management.commands.backtest_ordre_depouillement import (  # noqa: E402
    Command,
    ajuster,
    charger,
    choisir_cibles,
    ordres,
)

BASE = "var/backtest/snapshot.sqlite3"
GEOJSON = "data/K4voge_20220501_gf.geojson"
AVANCE = float(sys.argv[1]) if len(sys.argv) > 1 else 0.10
TIRAGES = int(sys.argv[2]) if len(sys.argv) > 2 else 10
# Variogramme exponentiel ajuste sur var/clusters_residus.py :
# correlation 0.31 a 2.5 km, 0.17 a 15 km, 0.07 a 30 km, nulle au-dela.
PALIER = 0.31
PORTEE = 25.0
VOISINS = 12


def coordonnees(chemin, communes):
    d = json.load(open(GEOJSON))
    centres = {}
    for f in d["features"]:
        geo = f["geometry"]
        anneaux = geo["coordinates"] if geo["type"] == "Polygon" else \
            [c for poly in geo["coordinates"] for c in poly]
        points = np.array([p for a in anneaux for p in a])
        centres[f["properties"]["vogeId"]] = points.mean(axis=0)
    conn = sqlite3.connect(f"file:{chemin}?mode=ro&immutable=1", uri=True)
    ofs = dict(conn.execute("select id, numero_ofs from scrutin_commune"))
    conn.close()
    manquant = np.array([np.nan, np.nan])
    xy = np.array([centres.get(ofs.get(cid), manquant) for cid, _ in communes])
    # degres -> km, projection locale suffisante a l'echelle de la Suisse
    return np.column_stack([xy[:, 0] * 111 * np.cos(np.radians(46.8)), xy[:, 1] * 111])


def correlation(distances):
    return PALIER * np.exp(-distances / PORTEE)


def krigeage(residus_obs, distances_obs, distances_croisees, volatilite_obs,
             volatilite_cible):
    """Residu attendu de chaque commune manquante, vu ses voisines depouillees.

    Krigeage simple sur les residus standardises, restreint aux plus proches
    voisins. C(0) = 1 et C(d) = palier*exp(-d/portee) : l'ecart entre les deux
    est l'effet de pepite, qui retrecit naturellement la correction vers zero.
    """
    standardise = residus_obs / volatilite_obs
    sortie = np.zeros(distances_croisees.shape[0])
    proches = np.argsort(distances_croisees, axis=1)[:, :VOISINS]
    for j in range(distances_croisees.shape[0]):
        idx = proches[j]
        c = correlation(distances_croisees[j, idx])
        if c.max() < 0.02:
            continue
        matrice = correlation(distances_obs[np.ix_(idx, idx)])
        np.fill_diagonal(matrice, 1.0)
        try:
            poids = np.linalg.solve(matrice, c)
        except np.linalg.LinAlgError:
            continue
        sortie[j] = poids @ standardise[idx]
    return sortie * volatilite_cible


def main():
    commande = Command()
    commande.nb_composantes = 6
    commande.seuil = 7
    sujets, communes, oui, non, elec, bul = charger(BASE)
    xy_toutes = coordonnees(BASE, communes)
    cibles = choisir_cibles(sujets, 20, 4, lambda m: None)
    print(f"{len(cibles)} cibles, avance {AVANCE:.0%}, {TIRAGES} tirages, "
          f"{VOISINS} voisins, portee {PORTEE:.0f} km\n")

    resultats = {"sans": [], "krigeage": [], "moyenne_voisins": []}
    correlations = []
    cache = {}
    for rang, cible in enumerate(cibles, 1):
        ctx = commande.contexte(cible, sujets, oui, non, elec, bul, cache)
        indice = cible[0]
        date = sujets[indice][2]
        anterieurs = [j for j, s in enumerate(sujets) if s[2] < date]
        valide, _ = cache[date]
        garde = valide & ~np.isnan(oui[:, indice]) & ~np.isnan(non[:, indice]) \
            & (elec[:, indice] > 0) & (bul[:, indice] > 0)
        xy = xy_toutes[garde].copy()
        # Le GeoJSON date de 2022, la base de 2026 : quelques communes fusionnees
        # n'ont pas de centroide. On les envoie a l'infini, chacune dans sa
        # direction : correlation nulle avec tout le monde, donc correction nulle,
        # et elles ne servent jamais de voisines.
        sans = np.isnan(xy).any(axis=1)
        if sans.any():
            xy[sans] = 1e6 + np.arange(sans.sum())[:, None] * 1e4
            print(f"  [{rang}] {date} : {sans.sum()} communes sans centroide, neutralisees")
        design = np.column_stack([ctx["composantes"], np.ones(ctx["nb_communes"])])

        # Volatilite historique de chaque commune, pour standardiser.
        sous_oui, sous_non = oui[garde][:, anterieurs], non[garde][:, anterieurs]
        p_hist = sous_oui / (sous_oui + sous_non)
        poids_hist = np.nan_to_num(bul[garde][:, anterieurs], nan=0.0)
        poids_hist = np.where(poids_hist > 0, poids_hist, sous_oui + sous_non)
        res_hist = np.empty_like(p_hist)
        for j in range(p_hist.shape[1]):
            res_hist[:, j] = p_hist[:, j] - design @ ajuster(design, p_hist[:, j],
                                                             poids_hist[:, j])
        volatilite = np.maximum(res_hist.std(axis=1), 1e-6)

        rng = np.random.default_rng(999 + ctx["sujet_id"])
        for _ in range(TIRAGES):
            ordre = ordres("realiste", ctx["pourcentage_oui"], ctx["composantes"],
                           ctx["electeurs"], rng)
            cumul = np.cumsum(ctx["exprimes"][ordre])
            k = max(int(np.searchsorted(cumul, AVANCE * cumul[-1]) + 1), 8)
            if k >= ctx["nb_communes"] - 20:
                continue
            dedans, hors = ordre[:k], ordre[k:]
            poids = ctx["bulletins"][dedans].astype(float)
            beta = ajuster(design[dedans], ctx["pourcentage_oui"][dedans], poids)
            beta_part = ajuster(design[dedans], ctx["participation"][dedans], poids)
            residus_obs = ctx["pourcentage_oui"][dedans] - design[dedans] @ beta
            votants = (design[hors] @ beta_part) * ctx["electeurs_precedents"][hors]
            oui_connu = ctx["oui_absolus"][dedans].sum()
            exprimes_connus = ctx["exprimes"][dedans].sum()

            d_obs = np.sqrt(((xy[dedans][:, None] - xy[dedans][None]) ** 2).sum(-1))
            d_croix = np.sqrt(((xy[hors][:, None] - xy[dedans][None]) ** 2).sum(-1))
            correction = krigeage(residus_obs, d_obs, d_croix,
                                  volatilite[dedans], volatilite[hors])
            # Variante naive : moyenne simple des voisins a moins de 15 km.
            proche = d_croix < 15.0
            naive = np.where(proche.any(axis=1),
                             (proche @ residus_obs) / np.maximum(proche.sum(1), 1), 0.0)

            reel = ctx["pourcentage_oui"][hors] - design[hors] @ beta
            fini = np.isfinite(correction) & np.isfinite(reel)
            if fini.sum() > 50 and correction[fini].std() > 0:
                correlations.append(np.corrcoef(correction[fini], reel[fini])[0, 1])

            for nom, decalage in (("sans", 0.0), ("krigeage", correction),
                                  ("moyenne_voisins", naive)):
                predit = design[hors] @ beta + decalage
                projete = ((oui_connu + (predit * votants).sum())
                           / (exprimes_connus + votants.sum()))
                resultats[nom].append(abs(projete - ctx["vrai_oui"]) * 100)
        print(f"  [{rang}/{len(cibles)}] {date}", flush=True)

    print(f"\nCorrelation entre residu predit par krigeage et residu reel : "
          f"{np.nanmedian(correlations):.3f} (mediane)")
    print(f"\n{'methode':>18} {'|err| mediane':>14} {'moyenne':>9} {'p90':>8}")
    for nom in ("sans", "krigeage", "moyenne_voisins"):
        v = np.array(resultats[nom])
        print(f"{nom:>18} {np.median(v):>13.3f} {v.mean():>9.3f} "
              f"{np.quantile(v, 0.9):>8.3f}")
    sans, avec = np.array(resultats["sans"]), np.array(resultats["krigeage"])
    mieux = (avec < sans).mean()
    print(f"\nLe krigeage ameliore dans {mieux:.0%} des cas, "
          f"gain median {np.median(sans - avec):+.3f} pt")


main()
