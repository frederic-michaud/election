"""Plan factoriel 2^3 : ponderation de l'ACP x nombre de composantes x effet canton.

Les trois leviers identifies, croises. L'effet canton entre comme indicatrices
dans le design ; `lstsq` renvoyant la solution de norme minimale, un canton dont
aucune commune n'est encore depouillee recoit un effet nul — le retrecissement
est donc automatique, sans hyperparametre.

    .venv/bin/python var/facteurs.py [tirages]
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
    ajuster,
    charger,
    choisir_cibles,
    ordres,
)

BASE = "var/backtest/snapshot.sqlite3"
TIRAGES = int(sys.argv[1]) if len(sys.argv) > 1 else 15
AVANCES = (0.05, 0.10, 0.25, 0.50)
PIRES = ["2025-09-28", "2020-02-09", "2018-11-25", "2022-02-13",
         "2021-09-26", "2021-03-07"]


def acp(matrice, poids, k):
    w = poids / poids.sum()
    centre = matrice - (matrice * w[:, None]).sum(axis=0)
    _, _, vt = np.linalg.svd(centre * np.sqrt(w)[:, None], full_matrices=False)
    return centre @ vt[:k].T


def main():
    sujets, communes, oui, non, elec, bul = charger(BASE)
    conn = sqlite3.connect(f"file:{BASE}?mode=ro&immutable=1", uri=True)
    cantons_id = dict(conn.execute("select id, canton_id from scrutin_commune"))
    conn.close()
    canton_tous = np.array([cantons_id.get(cid, -1) for cid, _ in communes])

    cibles = choisir_cibles(sujets, 20, 4, lambda m: None)
    variantes = [(p, k, c) for p in (False, True) for k in (6, 20)
                 for c in (False, True)]
    erreurs = {(v, a): [] for v in variantes for a in AVANCES}
    par_objet = {v: {} for v in variantes}
    print(f"{len(cibles)} cibles, {TIRAGES} tirages, {len(variantes)} variantes\n")

    for rang, cible in enumerate(cibles, 1):
        indice = cible[0]
        date = sujets[indice][2]
        anterieurs = [j for j, s in enumerate(sujets) if s[2] < date]
        so, sn = oui[:, anterieurs], non[:, anterieurs]
        valide = ~np.isnan(so).any(axis=1) & ~np.isnan(sn).any(axis=1)
        garde = valide & ~np.isnan(oui[:, indice]) & ~np.isnan(non[:, indice]) \
            & (elec[:, indice] > 0) & (bul[:, indice] > 0)
        matrice = so[valide] / (so[valide] + sn[valide])
        taille = np.maximum(np.nanmean(np.nan_to_num(bul[valide][:, anterieurs],
                                                     nan=0.0), axis=1), 1.0)
        # Les 6 premieres composantes d'une ACP a 20 sont celles d'une ACP a 6.
        comp = {False: acp(matrice, np.ones(len(matrice)), 20)[garde[valide]],
                True: acp(matrice, taille, 20)[garde[valide]]}

        canton = canton_tous[garde]
        codes = np.unique(canton)
        indicatrices = (canton[:, None] == codes[None, :]).astype(float)

        precedent = max(anterieurs, key=lambda j: sujets[j][2])
        expr = oui[garde, indice] + non[garde, indice]
        pct, part = oui[garde, indice] / expr, expr / elec[garde, indice]
        bulletins, elec_prec = bul[garde, indice], elec[garde, precedent]
        oui_abs, nb = oui[garde, indice], int(garde.sum())
        vrai = oui_abs.sum() / expr.sum()

        designs = {}
        for pondere in (False, True):
            for k in (6, 20):
                for avec_canton in (False, True):
                    bloc = [comp[pondere][:, :k]]
                    if avec_canton:
                        bloc.append(indicatrices)
                    bloc.append(np.ones((nb, 1)))
                    designs[(pondere, k, avec_canton)] = np.column_stack(bloc)

        rng = np.random.default_rng(2024 + sujets[indice][1])
        local = {v: [] for v in variantes}
        for _ in range(TIRAGES):
            ordre = ordres("realiste", pct, comp[False][:, :6],
                           elec[garde, indice], rng)
            cumul = np.cumsum(expr[ordre])
            for avance in AVANCES:
                k_com = max(int(np.searchsorted(cumul, avance * cumul[-1]) + 1), 8)
                if k_com >= nb - 10:
                    continue
                dedans, hors = ordre[:k_com], ordre[k_com:]
                w = bulletins[dedans].astype(float)
                for v in variantes:
                    design = designs[v]
                    b_oui = ajuster(design[dedans], pct[dedans], w)
                    b_part = ajuster(design[dedans], part[dedans], w)
                    votants = (design[hors] @ b_part) * elec_prec[hors]
                    projete = ((oui_abs[dedans].sum()
                                + ((design[hors] @ b_oui) * votants).sum())
                               / (expr[dedans].sum() + votants.sum()))
                    err = abs(projete - vrai) * 100
                    erreurs[(v, avance)].append(err)
                    if avance == 0.25:
                        local[v].append(err)
        for v in variantes:
            if local[v]:
                par_objet[v][date] = float(np.median(local[v]))
        print(f"  [{rang}/{len(cibles)}] {date}", flush=True)

    print(f"\n{'ACP':>10} {'axes':>5} {'canton':>7}" +
          "".join(f"{f'@{a:.0%}':>9}" for a in AVANCES) + f"{'6 pires @25%':>14}")
    print("-" * 74)
    for v in variantes:
        pondere, k, avec = v
        pires = [par_objet[v][d] for d in PIRES if d in par_objet[v]]
        ligne = (f"{'pondérée' if pondere else 'uniforme':>10} {k:>5} "
                 f"{'oui' if avec else 'non':>7}")
        for a in AVANCES:
            ligne += f"{np.median(erreurs[(v, a)]):>9.3f}"
        marque = "   <- production" if v == (False, 6, False) else ""
        print(ligne + f"{np.median(pires):>14.3f}" + marque)

    print("\nDétail des 6 pires objets, erreur médiane à 25% d'avance")
    entetes = [f"{'p' if p else 'u'}{k}{'+c' if c else ''}" for p, k, c in variantes]
    print(f"{'date':>12}" + "".join(f"{h:>8}" for h in entetes))
    for d in PIRES:
        print(f"{d:>12}" + "".join(f"{par_objet[v].get(d, float('nan')):>8.2f}"
                                   for v in variantes))


main()
