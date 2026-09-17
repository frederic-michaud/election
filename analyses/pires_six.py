"""%oui projete a 25% de depouillement, pour les six objets les plus rates."""
import os
import pathlib
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


def acp(matrice, poids, k):
    """ACP ponderee : axes principaux de la distribution ponderee par `poids`."""
    w = poids / poids.sum()
    centre = matrice - (matrice * w[:, None]).sum(axis=0)
    _, _, vt = np.linalg.svd(centre * np.sqrt(w)[:, None], full_matrices=False)
    return centre @ vt[:k].T


PIRES = ["2025-09-28", "2020-02-09", "2018-11-25", "2022-02-13",
         "2021-09-26", "2021-03-07"]
AVANCE, TIRAGES = 0.25, 15

sujets, communes, oui, non, elec, bul = charger("var/backtest/snapshot.sqlite3")
cibles = [c for c in choisir_cibles(sujets, 20, 4, lambda m: None)
          if sujets[c[0]][2] in PIRES]

print(f"{'date':>12} {'objet':<34} {'sans pond.':>11} {'avec pond.':>11} "
      f"{'nu':>8} {'final':>8}")
print("-" * 88)
for cible in sorted(cibles, key=lambda c: PIRES.index(sujets[c[0]][2])):
    indice = cible[0]
    date = sujets[indice][2]
    anterieurs = [j for j, s in enumerate(sujets) if s[2] < date]
    so, sn = oui[:, anterieurs], non[:, anterieurs]
    valide = ~np.isnan(so).any(axis=1) & ~np.isnan(sn).any(axis=1)
    garde = valide & ~np.isnan(oui[:, indice]) & ~np.isnan(non[:, indice]) \
        & (elec[:, indice] > 0) & (bul[:, indice] > 0)
    matrice = so[valide] / (so[valide] + sn[valide])
    taille = np.maximum(np.nanmean(np.nan_to_num(bul[valide][:, anterieurs], nan=0.0),
                                   axis=1), 1.0)
    comp = {False: acp(matrice, np.ones(len(matrice)), 6)[garde[valide]],
            True: acp(matrice, taille, 6)[garde[valide]]}

    precedent = max(anterieurs, key=lambda j: sujets[j][2])
    expr = oui[garde, indice] + non[garde, indice]
    pct, part = oui[garde, indice] / expr, expr / elec[garde, indice]
    bulletins, elec_prec = bul[garde, indice], elec[garde, precedent]
    oui_abs, nb = oui[garde, indice], int(garde.sum())
    vrai = oui_abs.sum() / expr.sum()

    rng = np.random.default_rng(2024 + sujets[indice][1])
    proj = {False: [], True: []}
    nus = []
    for _ in range(TIRAGES):
        ordre = ordres("realiste", pct, comp[False], elec[garde, indice], rng)
        cumul = np.cumsum(expr[ordre])
        k = max(int(np.searchsorted(cumul, AVANCE * cumul[-1]) + 1), 8)
        dedans, hors = ordre[:k], ordre[k:]
        w = bulletins[dedans].astype(float)
        nus.append(oui_abs[dedans].sum() / expr[dedans].sum())
        for pondere in (False, True):
            design = np.column_stack([comp[pondere], np.ones(nb)])
            b_oui = ajuster(design[dedans], pct[dedans], w)
            b_part = ajuster(design[dedans], part[dedans], w)
            votants = (design[hors] @ b_part) * elec_prec[hors]
            proj[pondere].append(
                (oui_abs[dedans].sum() + ((design[hors] @ b_oui) * votants).sum())
                / (expr[dedans].sum() + votants.sum()))
    nom = sujets[indice][3][:34]
    print(f"{date:>12} {nom:<34} {100*np.median(proj[False]):>10.2f}% "
          f"{100*np.median(proj[True]):>10.2f}% {100*np.median(nus):>7.2f}% "
          f"{100*vrai:>7.2f}%")
