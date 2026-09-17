"""Ou se situe 2020-02-09 (logements abordables) parmi les 30 objets ?"""
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
)

sujets, communes, oui, non, elec, bul = charger("var/backtest/snapshot.sqlite3")


def acp(matrice, poids, k):
    w = poids / poids.sum()
    centre = matrice - (matrice * w[:, None]).sum(axis=0)
    _, _, vt = np.linalg.svd(centre * np.sqrt(w)[:, None], full_matrices=False)
    return centre @ vt[:k].T


lignes = []
for cible in choisir_cibles(sujets, 20, 4, lambda m: None):
    indice = cible[0]
    date = sujets[indice][2]
    ant = [j for j, s in enumerate(sujets) if s[2] < date]
    so, sn = oui[:, ant], non[:, ant]
    valide = ~np.isnan(so).any(axis=1) & ~np.isnan(sn).any(axis=1)
    garde = valide & ~np.isnan(oui[:, indice]) & ~np.isnan(non[:, indice]) \
        & (elec[:, indice] > 0) & (bul[:, indice] > 0)
    comp = acp(so[valide] / (so[valide] + sn[valide]),
               np.ones(int(valide.sum())), 6)[garde[valide]]
    expr = oui[garde, indice] + non[garde, indice]
    pct = oui[garde, indice] / expr
    taille = elec[garde, indice]
    w = bul[garde, indice].astype(float)

    design = np.column_stack([comp, np.ones(len(comp))])
    beta = ajuster(design, pct, w)
    res = pct - design @ beta
    moy = lambda x: (x * w).sum() / w.sum()  # noqa: E731
    sigma = np.sqrt(moy((res - moy(res)) ** 2))
    var_y = np.sqrt(moy((pct - moy(pct)) ** 2))

    # Pente du %oui contre la taille : combien de points entre petite et grande.
    lt = np.log10(np.maximum(taille, 1))
    pente = np.polyfit(lt, pct, 1)[0] * 100
    # Ce que la taille explique encore APRES l'ACP.
    pente_res = np.polyfit(lt, res, 1)[0] * 100
    lignes.append((date, sujets[indice][3][:30], pente, pente_res,
                   1 - (sigma / var_y) ** 2, 100 * sigma))

print(f"{'date':>12} {'objet':<31} {"pt/décade":>11} {'après ACP':>10} "
      f"{'R2':>6} {'sigma':>6}")
print("-" * 84)
for x in sorted(lignes, key=lambda r: -abs(r[2])):
    marque = "  <---" if x[0] == "2020-02-09" else ""
    print(f"{x[0]:>12} {x[1]:<31} {x[2]:>12.2f} {x[3]:>10.2f} {x[4]:>6.2f} "
          f"{x[5]:>6.2f}{marque}")
