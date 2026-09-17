"""Faut-il ponderer l'ACP, et avec quel exposant ponderer le fit ?

Constat de depart : la regression est deja ponderee par les bulletins
(extrapolation.py), mais l'ACP ne l'est pas — `PCA().fit_transform(X)` met
Zurich et un hameau de 50 electeurs sur le meme pied. Les 6 axes representent
donc surtout la masse des petites communes.

On teste deux leviers, sur le meme backtest :
  - ACP ponderee par la taille (SVD de sqrt(w)*(X - moyenne ponderee)) ;
  - exposant alpha du poids de la regression : w = bulletins^alpha.
    alpha=1 est la production. alpha=0 ignore la taille. La variante
    « variance » utilise 1/(sigma^2 + p(1-p)/n), le poids optimal au sens des
    moindres carres, qui sature des que le residu structurel domine le bruit
    d'echantillonnage.

    .venv/bin/python var/ponderation.py [tirages]
"""
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

BASE = "var/backtest/snapshot.sqlite3"
TIRAGES = int(sys.argv[1]) if len(sys.argv) > 1 else 15
AVANCES = (0.05, 0.10, 0.25, 0.50)
NB_COMPOSANTES = 6
SIGMA_STRUCTUREL = 0.033  # 3,3 points, mesure dans RESULTATS_BACKTEST.md


def acp(matrice, poids, k):
    """ACP ponderee : axes principaux de la distribution ponderee par `poids`.

    poids uniforme redonne l'ACP de sklearn (au signe des axes pres).
    """
    w = poids / poids.sum()
    centre = matrice - (matrice * w[:, None]).sum(axis=0)
    _, _, vt = np.linalg.svd(centre * np.sqrt(w)[:, None], full_matrices=False)
    return centre @ vt[:k].T


def poids_fit(nom, bulletins, electeurs):
    if nom == "variance":
        return 1.0 / (SIGMA_STRUCTUREL**2 + 0.25 / np.maximum(electeurs, 1))
    return np.maximum(bulletins, 1.0) ** float(nom)


def main():
    sujets, communes, oui, non, elec, bul = charger(BASE)
    cibles = choisir_cibles(sujets, 20, 4, lambda m: None)
    variantes = [(acp_p, a) for acp_p in (False, True)
                 for a in ("0", "0.5", "1", "1.5", "variance")]
    erreurs = {(v, av): [] for v in variantes for av in AVANCES}
    print(f"{len(cibles)} cibles, {TIRAGES} tirages, {len(variantes)} variantes\n")

    for rang, cible in enumerate(cibles, 1):
        indice = cible[0]
        date = sujets[indice][2]
        anterieurs = [j for j, s in enumerate(sujets) if s[2] < date]
        sous_oui, sous_non = oui[:, anterieurs], non[:, anterieurs]
        valide = ~np.isnan(sous_oui).any(axis=1) & ~np.isnan(sous_non).any(axis=1)
        garde = valide & ~np.isnan(oui[:, indice]) & ~np.isnan(non[:, indice]) \
            & (elec[:, indice] > 0) & (bul[:, indice] > 0)

        matrice = (sous_oui[valide] / (sous_oui[valide] + sous_non[valide]))
        taille = np.nanmean(np.nan_to_num(bul[valide][:, anterieurs], nan=0.0), axis=1)
        taille = np.maximum(taille, 1.0)
        composantes = {
            False: acp(matrice, np.ones(len(matrice)), NB_COMPOSANTES)[garde[valide]],
            True: acp(matrice, taille, NB_COMPOSANTES)[garde[valide]],
        }

        precedent = max(anterieurs, key=lambda j: sujets[j][2])
        exprimes = oui[garde, indice] + non[garde, indice]
        pourcentage = oui[garde, indice] / exprimes
        participation = exprimes / elec[garde, indice]
        bulletins = bul[garde, indice]
        electeurs_prec = elec[garde, precedent]
        oui_abs = oui[garde, indice]
        vrai = oui_abs.sum() / exprimes.sum()
        nb = int(garde.sum())

        rng = np.random.default_rng(2024 + sujets[indice][1])
        for _ in range(TIRAGES):
            ordre = ordres("realiste", pourcentage, composantes[False],
                           elec[garde, indice], rng)
            cumul = np.cumsum(exprimes[ordre])
            for avance in AVANCES:
                k = max(int(np.searchsorted(cumul, avance * cumul[-1]) + 1), 8)
                if k >= nb - 10:
                    continue
                dedans, hors = ordre[:k], ordre[k:]
                for acp_pondere, alpha in variantes:
                    design = np.column_stack([composantes[acp_pondere], np.ones(nb)])
                    w = poids_fit(alpha, bulletins[dedans], electeurs_prec[dedans])
                    b_oui = ajuster(design[dedans], pourcentage[dedans], w)
                    b_part = ajuster(design[dedans], participation[dedans], w)
                    votants = (design[hors] @ b_part) * electeurs_prec[hors]
                    projete = ((oui_abs[dedans].sum()
                                + ((design[hors] @ b_oui) * votants).sum())
                               / (exprimes[dedans].sum() + votants.sum()))
                    erreurs[((acp_pondere, alpha), avance)].append(
                        abs(projete - vrai) * 100)
        print(f"  [{rang}/{len(cibles)}] {date}", flush=True)

    reference = ((False, "1"), )
    print(f"\n{'ACP':>12} {'poids fit':>10}" + "".join(f"{f'@{a:.0%}':>9}" for a in AVANCES))
    print("-" * 62)
    for v in variantes:
        libelle = "ponderee" if v[0] else "uniforme"
        marque = "  <- production" if v == reference[0] else ""
        ligne = f"{libelle:>12} {v[1]:>10}"
        for a in AVANCES:
            ligne += f"{np.median(erreurs[(v, a)]):>9.3f}"
        print(ligne + marque)

    print("\nGain apparie contre la production (positif = mieux), a 10% d'avance")
    base = np.array(erreurs[(reference[0], 0.10)])
    for v in variantes:
        if v == reference[0]:
            continue
        autre = np.array(erreurs[(v, 0.10)])
        n = min(len(base), len(autre))
        diff = base[:n] - autre[:n]
        libelle = ("ponderee" if v[0] else "uniforme") + " / " + v[1]
        print(f"  {libelle:>22} : gain median {np.median(diff):+.3f} pt, "
              f"mieux dans {(diff > 0).mean():.0%} des cas")


main()
