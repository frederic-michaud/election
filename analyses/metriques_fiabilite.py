"""Quelles metriques observables le jour J annoncent une projection qui rate ?

Pour chaque objet cible, on rejoue un debut de soiree en ordre realiste, on
s'arrete a une avance donnee, et on calcule sur les seules communes deja
depouillees une batterie d'indicateurs. On les confronte ensuite a l'erreur
reelle de la projection, sur deux axes :

  entre objets  — la metrique repere-t-elle les votations difficiles ?
  intra-objet   — d'un ordre d'arrivee a l'autre, repere-t-elle la soiree qui rate ?

Le r de Pearson echoue aux deux (cf. RESULTATS_BACKTEST.md) : il mesure la
dispersion des residus, alors que l'erreur vient de leur moyenne sur
l'echantillon retenu.

    .venv/bin/python var/metriques_fiabilite.py [avance] [tirages]
"""
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
AVANCE = float(sys.argv[1]) if len(sys.argv) > 1 else 0.10
TIRAGES = int(sys.argv[2]) if len(sys.argv) > 2 else 30


def metadonnees(chemin, communes):
    conn = sqlite3.connect(f"file:{chemin}?mode=ro&immutable=1", uri=True)
    lignes = dict((r[0], (r[1], str(r[2]), str(r[3]))) for r in conn.execute(
        "select id, canton_id, langue, degre_urbanisation from scrutin_commune"))
    conn.close()
    defaut = (-1, "?", "?")
    return [lignes.get(cid, defaut) for cid, _ in communes]


def moyenne_ponderee(x, w):
    return (x * w).sum(axis=0) / w.sum()


def ecart_type_pondere(x, w):
    moyenne = moyenne_ponderee(x, w)
    return np.sqrt((w * (x - moyenne) ** 2).sum() / w.sum())


def residus_historiques(composantes, oui, non, bul, garde, anterieurs):
    """Residu de chaque commune a chaque objet passe, avec le meme modele.

    Donne la volatilite propre de chaque commune : une commune « normalement
    bien predite » est une commune dont le residu historique est petit.
    """
    design = np.column_stack([composantes, np.ones(len(composantes))])
    sous_oui, sous_non = oui[garde][:, anterieurs], non[garde][:, anterieurs]
    exprimes = sous_oui + sous_non
    pourcentages = sous_oui / exprimes
    poids = np.nan_to_num(bul[garde][:, anterieurs], nan=0.0)
    poids = np.where(poids > 0, poids, exprimes)
    residus = np.empty_like(pourcentages)
    for j in range(pourcentages.shape[1]):
        beta = ajuster(design, pourcentages[:, j], poids[:, j])
        residus[:, j] = pourcentages[:, j] - design @ beta
    return residus


def metriques(ctx, ordre, k, volatilite, meta_canton, meta_urbain):
    """Tout ce qu'on peut calculer a partir des seules communes depouillees."""
    design = np.column_stack([ctx["composantes"], np.ones(ctx["nb_communes"])])
    dedans = ordre[:k]
    poids = ctx["bulletins"][dedans].astype(float)
    y = ctx["pourcentage_oui"][dedans]
    beta = ajuster(design[dedans], y, poids)
    residus = y - design[dedans] @ beta

    sigma = ecart_type_pondere(residus, poids) * 100
    variance_y = ecart_type_pondere(y, poids) * 100
    s = np.maximum(volatilite[dedans] * 100, 1e-9)
    standardise = np.abs(residus * 100) / s

    # Communes « normalement previsibles » : volatilite historique dans le
    # tercile bas, et taille moyenne (ni hameau ni grande ville).
    electeurs = ctx["electeurs_precedents"][dedans]
    seuil_vol = np.quantile(volatilite, 1 / 3) * 100
    bas, haut = np.quantile(ctx["electeurs_precedents"], [0.5, 0.95])
    fiables = (s <= seuil_vol) & (electeurs >= bas) & (electeurs <= haut)

    # Representativite observable de l'echantillon depouille.
    centre_dedans = moyenne_ponderee(ctx["composantes"][dedans], poids[:, None])
    poids_tous = ctx["bulletins"][:, None].astype(float)
    centre_tous = moyenne_ponderee(ctx["composantes"], poids_tous)
    dispersion = ctx["composantes"].std(axis=0)
    ecart_profil = np.abs((centre_dedans - centre_tous) / dispersion)

    # Derive des coefficients entre la moitie de l'echantillon et la totalite.
    moitie = ordre[: max(8, k // 2)]
    beta_moitie = ajuster(design[moitie], ctx["pourcentage_oui"][moitie],
                          ctx["bulletins"][moitie].astype(float))
    derive = np.linalg.norm(beta - beta_moitie) / (np.linalg.norm(beta) + 1e-12)

    # Structure cantonale residuelle : part de variance inter-cantons.
    cantons = meta_canton[dedans]
    inter, total = 0.0, (poids * residus**2).sum()
    for c in np.unique(cantons):
        m = cantons == c
        if m.sum() >= 3:
            inter += poids[m].sum() * moyenne_ponderee(residus[m], poids[m]) ** 2
    part_canton = inter / total if total > 0 else np.nan

    # Meme chose sur le degre d'urbanisation : le biais ville/campagne direct.
    inter_u = 0.0
    urbain = meta_urbain[dedans]
    for u in np.unique(urbain):
        m = urbain == u
        if m.sum() >= 3:
            inter_u += poids[m].sum() * moyenne_ponderee(residus[m], poids[m]) ** 2
    part_urbain = inter_u / total if total > 0 else np.nan


    # --- sensibilites : de combien la projection bougerait-elle ? ----------
    # Elles ne mesurent pas la dispersion des residus mais la dependance de la
    # projection a une hypothese — plus proche de ce qui fait rater une soiree.
    hors = ordre[k:]
    beta_part = ajuster(design[dedans], ctx["participation"][dedans], poids)
    votants = (design[hors] @ beta_part) * ctx["electeurs_precedents"][hors]
    oui_connu = ctx["oui_absolus"][dedans].sum()
    exprimes_connus = ctx["exprimes"][dedans].sum()

    def projeter(coefficients, decalage=None):
        predit = design[hors] @ coefficients
        if decalage is not None:
            predit = predit + decalage
        return ((oui_connu + (predit * votants).sum())
                / (exprimes_connus + votants.sum()))

    base = projeter(beta)

    # 1. Part du poids restant dans des cantons dont on n'a encore rien vu.
    vus = set(np.unique(meta_canton[dedans]).tolist())
    inconnus = np.array([c not in vus for c in meta_canton[hors]])
    poids_cantons_absents = (votants[inconnus].sum() / votants.sum()
                             if votants.sum() > 0 else np.nan)

    # 2. Effet canton : on recolle a chaque commune manquante le residu moyen
    #    de son canton, quand il est connu. L'ecart a la projection nue dit de
    #    combien une structure regionale non modelisee nous deplacerait.
    moyennes = {}
    for c in np.unique(cantons):
        m = cantons == c
        if m.sum() >= 3:
            moyennes[c] = moyenne_ponderee(residus[m], poids[m])
    decalage = np.array([moyennes.get(c, 0.0) for c in meta_canton[hors]])
    correction_canton = (projeter(beta, decalage) - base) * 100
    residu_canton_max = (max(abs(v) for v in moyennes.values()) * 100
                         if moyennes else np.nan)

    # 3. Jackknife par canton : on retire un canton entier de l'ajustement.
    #    Plus honnete qu'un bootstrap iid, qui ignore la structure par blocs.
    projections = []
    for c in moyennes:
        reste = cantons != c
        if reste.sum() > 10:
            beta_c = ajuster(design[dedans][reste], y[reste], poids[reste])
            projections.append(projeter(beta_c))
    jackknife_canton = np.std(projections) * 100 if len(projections) > 2 else np.nan

    # 4. Saut de la projection entre la moitie de l'echantillon et maintenant.
    beta_m = ajuster(design[moitie], ctx["pourcentage_oui"][moitie],
                     ctx["bulletins"][moitie].astype(float))
    saut_projection = abs(projeter(beta_m) - base) * 100

    gram = (design[dedans] * poids[:, None]).T @ design[dedans]
    inverse = np.linalg.inv(gram)
    leviers = np.einsum("ni,ij,nj->n", design[hors], inverse, design[hors])

    return {
        "sigma": sigma,
        "r2": 1 - (sigma / variance_y) ** 2 if variance_y > 0 else np.nan,
        "sigma_sur_hist": sigma / (np.median(volatilite) * 100),
        "exces_median": np.median(standardise),
        "exces_p90": np.quantile(standardise, 0.90),
        "poids_outliers_2s": poids[standardise > 2].sum() / poids.sum(),
        "poids_outliers_3s": poids[standardise > 3].sum() / poids.sum(),
        "exces_fiables": np.median(standardise[fiables]) if fiables.sum() >= 5 else np.nan,
        "outliers_fiables": (poids[fiables & (standardise > 2)].sum()
                             / poids[fiables].sum()) if fiables.sum() >= 5 else np.nan,
        "kurtosis": float(((standardise**4).mean() / (standardise**2).mean() ** 2)),
        "ecart_profil_max": ecart_profil.max(),
        "ecart_profil_1": ecart_profil[0],
        "part_canton": part_canton,
        "part_urbain": part_urbain,
        "derive_beta": derive,
        "levier_max": leviers.max() if leviers.size else np.nan,
        "poids_cantons_absents": poids_cantons_absents,
        "correction_canton": abs(correction_canton),
        "residu_canton_max": residu_canton_max,
        "jackknife_canton": jackknife_canton,
        "saut_projection": saut_projection,
        "nb_communes": float(k),
    }


def spearman(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 5 or np.ptp(a[ok]) == 0 or np.ptp(b[ok]) == 0:
        return np.nan
    rang = lambda v: np.argsort(np.argsort(v))  # noqa: E731
    return float(np.corrcoef(rang(a[ok]), rang(b[ok]))[0, 1])


def main():
    commande = Command()
    commande.nb_composantes = 6
    commande.seuil = 7
    sujets, communes, oui, non, elec, bul = charger(BASE)
    meta = metadonnees(BASE, communes)
    cibles = choisir_cibles(sujets, 20, 4, lambda m: None)
    print(f"{len(cibles)} cibles, avance {AVANCE:.0%}, {TIRAGES} tirages\n")

    par_objet, cache = [], {}
    for rang, cible in enumerate(cibles, 1):
        ctx = commande.contexte(cible, sujets, oui, non, elec, bul, cache)
        indice = cible[0]
        date = sujets[indice][2]
        anterieurs = [j for j, s in enumerate(sujets) if s[2] < date]
        garde = np.zeros(len(communes), bool)
        # `contexte` a filtre les communes : on reconstruit le meme masque.
        valide, _ = cache[date]
        cible_ok = ~np.isnan(oui[:, indice]) & ~np.isnan(non[:, indice]) \
            & (elec[:, indice] > 0) & (bul[:, indice] > 0)
        garde = valide & cible_ok
        residus_h = residus_historiques(ctx["composantes"], oui, non, bul,
                                        garde, anterieurs)
        volatilite = residus_h.std(axis=1)
        canton = np.array([meta[i][0] for i in np.where(garde)[0]])
        urbain = np.array([meta[i][2] for i in np.where(garde)[0]])

        rng = np.random.default_rng(12345 + ctx["sujet_id"])
        lignes = []
        for _ in range(TIRAGES):
            ordre = ordres("realiste", ctx["pourcentage_oui"], ctx["composantes"],
                           ctx["electeurs"], rng)
            cumul = np.cumsum(ctx["exprimes"][ordre])
            k = int(np.searchsorted(cumul, AVANCE * cumul[-1]) + 1)
            k = max(k, 8)
            if k >= ctx["nb_communes"] - 5:
                continue
            m = metriques(ctx, ordre, k, volatilite, canton, urbain)

            design = np.column_stack([ctx["composantes"], np.ones(ctx["nb_communes"])])
            dedans, hors = ordre[:k], ordre[k:]
            poids = ctx["bulletins"][dedans].astype(float)
            beta_oui = ajuster(design[dedans], ctx["pourcentage_oui"][dedans], poids)
            beta_part = ajuster(design[dedans], ctx["participation"][dedans], poids)
            votants = (design[hors] @ beta_part) * ctx["electeurs_precedents"][hors]
            projete = ((ctx["oui_absolus"][dedans].sum()
                        + ((design[hors] @ beta_oui) * votants).sum())
                       / (ctx["exprimes"][dedans].sum() + votants.sum()))
            m["erreur"] = abs(projete - ctx["vrai_oui"]) * 100
            m["erreur_signee"] = (projete - ctx["vrai_oui"]) * 100
            lignes.append(m)
        if lignes:
            par_objet.append((ctx, lignes))
        print(f"  [{rang}/{len(cibles)}] {ctx['date']} — {len(lignes)} tirages, "
              f"|err| mediane {np.median([x['erreur'] for x in lignes]):.2f} pt")

    noms = [c for c in par_objet[0][1][0] if not c.startswith("erreur")]
    import csv
    chemin = f"var/metriques_{int(AVANCE * 100):02d}.csv"
    with open(chemin, "w", newline="") as fichier:
        plume = csv.writer(fichier)
        plume.writerow(["date", "sujet", "erreur"] + noms)
        for ctx, lignes in par_objet:
            plume.writerow([ctx["date"], ctx["sujet_id"],
                            f"{np.median([x['erreur'] for x in lignes]):.5f}"]
                           + [f"{np.median([x[n] for x in lignes]):.6g}" for n in noms])
    print(f"ecrit {chemin}")
    print(f"\n{'metrique':>20} | {'entre objets':>12} {'p':>7} | {'intra-objet':>12} "
          f"| {'|corr| signe':>12}")
    print("-" * 78)
    resultats = []
    for nom in noms:
        entre_x = np.array([np.median([x[nom] for x in lignes]) for _, lignes in par_objet])
        entre_y = np.array([np.median([x["erreur"] for x in lignes]) for _, lignes in par_objet])
        rho_entre = spearman(entre_x, entre_y)
        intra = [spearman(np.array([x[nom] for x in lignes]),
                          np.array([x["erreur"] for x in lignes]))
                 for _, lignes in par_objet]
        rho_intra = np.nanmedian(intra)
        # Sur l'erreur signee, pour voir si la metrique annonce une direction.
        signe = [spearman(np.array([x[nom] for x in lignes]),
                          np.array([x["erreur_signee"] for x in lignes]))
                 for _, lignes in par_objet]
        n = np.isfinite(entre_x).sum()
        p = 2 * (1 - 0.5 * (1 + __import__("math").erf(abs(rho_entre) * np.sqrt(n - 1) / np.sqrt(2)))) \
            if np.isfinite(rho_entre) else np.nan
        resultats.append((abs(rho_intra) if np.isfinite(rho_intra) else 0, nom,
                          rho_entre, p, rho_intra, np.nanmedian(signe)))
    for _, nom, rho_entre, p, rho_intra, signe in sorted(resultats, reverse=True):
        print(f"{nom:>20} | {rho_entre:>12.2f} {p:>7.3f} | {rho_intra:>12.2f} "
              f"| {signe:>12.2f}")


main()
