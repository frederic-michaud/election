"""Deux figures sur la queue : la distribution des 30 objets, et les leviers.

La premiere montre que le probleme n'est pas le cas median mais quelques
votations ; la seconde, ce que chaque levier fait a cette queue.

    .venv/bin/python analyses/figure_outliers.py
"""
import os
import pathlib
import sys

import django
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "election.settings")
django.setup()

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

from scrutin.management.commands.backtest_ordre_depouillement import (  # noqa: E402
    ajuster,
    charger,
    choisir_cibles,
    ordres,
)

BASE = "var/backtest/snapshot.sqlite3"
AVANCE, TIRAGES = 0.25, 15
BLEU, ORANGE, AQUA, NEUTRE = "#2a78d6", "#eb6834", "#1baf7a", "#52514e"
FOND, ENCRE, GRIS = "#fcfcfb", "#0b0b0b", "#52514e"
VARIANTES = [("nu", "sans extrapolation", NEUTRE),
             ("u6", "6 axes  (production)", BLEU),
             ("p6", "ACP pondérée · 6 axes", BLEU),
             ("u6t", "6 axes · log(taille)", AQUA),
             ("u20", "20 axes", ORANGE),
             ("p20t", "ACP pondérée · 20 axes · log(taille)", ORANGE)]


def acp(matrice, poids, k):
    w = poids / poids.sum()
    centre = matrice - (matrice * w[:, None]).sum(axis=0)
    _, _, vt = np.linalg.svd(centre * np.sqrt(w)[:, None], full_matrices=False)
    return centre @ vt[:k].T


def calculer():
    sujets, communes, oui, non, elec, bul = charger(BASE)
    resultats = {}
    for rang, cible in enumerate(choisir_cibles(sujets, 20, 4, lambda m: None), 1):
        indice = cible[0]
        date = sujets[indice][2]
        ant = [j for j, s in enumerate(sujets) if s[2] < date]
        so, sn = oui[:, ant], non[:, ant]
        valide = ~np.isnan(so).any(axis=1) & ~np.isnan(sn).any(axis=1)
        garde = valide & ~np.isnan(oui[:, indice]) & ~np.isnan(non[:, indice]) \
            & (elec[:, indice] > 0) & (bul[:, indice] > 0)
        matrice = so[valide] / (so[valide] + sn[valide])
        taille_h = np.maximum(np.nanmean(
            np.nan_to_num(bul[valide][:, ant], nan=0.0), axis=1), 1.0)
        comp_u = acp(matrice, np.ones(len(matrice)), 20)[garde[valide]]
        comp_p = acp(matrice, taille_h, 20)[garde[valide]]

        precedent = max(ant, key=lambda j: sujets[j][2])
        expr = oui[garde, indice] + non[garde, indice]
        pct, part = oui[garde, indice] / expr, expr / elec[garde, indice]
        bulletins, elec_prec = bul[garde, indice], elec[garde, precedent]
        oui_abs, nb = oui[garde, indice], int(garde.sum())
        vrai = oui_abs.sum() / expr.sum()
        lt = np.log10(np.maximum(elec_prec, 1.0))
        lt = ((lt - lt.mean()) / lt.std())[:, None]
        un = np.ones((nb, 1))
        designs = {"u6": np.column_stack([comp_u[:, :6], un]),
                   "p6": np.column_stack([comp_p[:, :6], un]),
                   "u6t": np.column_stack([comp_u[:, :6], lt, un]),
                   "u20": np.column_stack([comp_u, un]),
                   "p20t": np.column_stack([comp_p, lt, un])}

        rng = np.random.default_rng(2024 + sujets[indice][1])
        erreurs = {c: [] for c in list(designs) + ["nu"]}
        for _ in range(TIRAGES):
            ordre = ordres("realiste", pct, comp_u[:, :6], elec[garde, indice], rng)
            cumul = np.cumsum(expr[ordre])
            k = max(int(np.searchsorted(cumul, AVANCE * cumul[-1]) + 1), 8)
            dedans, hors = ordre[:k], ordre[k:]
            w = bulletins[dedans].astype(float)
            erreurs["nu"].append(abs(oui_abs[dedans].sum() / expr[dedans].sum()
                                     - vrai) * 100)
            for cle, design in designs.items():
                b_oui = ajuster(design[dedans], pct[dedans], w)
                b_part = ajuster(design[dedans], part[dedans], w)
                votants = (design[hors] @ b_part) * elec_prec[hors]
                projete = ((oui_abs[dedans].sum()
                            + ((design[hors] @ b_oui) * votants).sum())
                           / (expr[dedans].sum() + votants.sum()))
                erreurs[cle].append(abs(projete - vrai) * 100)
        resultats[date] = {c: float(np.median(v)) for c, v in erreurs.items()}
        print(f"  [{rang}/30] {date}", flush=True)
    return resultats


def habiller(axe):
    axe.set_facecolor(FOND)
    axe.set_axisbelow(True)
    for cote in ("top", "right"):
        axe.spines[cote].set_visible(False)
    for cote in ("left", "bottom"):
        axe.spines[cote].set_color("#c9c6bf")
    axe.tick_params(labelsize=8.5, colors=GRIS)


def figure_distribution(resultats):
    """Les 30 objets tries : la queue, et ce qu'elle devient."""
    dates = sorted(resultats, key=lambda d: -resultats[d]["u6"])
    x = np.arange(len(dates))
    figure, axe = plt.subplots(figsize=(12.5, 5.6), facecolor=FOND)
    axe.bar(x - 0.21, [resultats[d]["u6"] for d in dates], width=0.42,
            color=BLEU, label="6 axes  (production)", zorder=3)
    axe.bar(x + 0.21, [resultats[d]["p20t"] for d in dates], width=0.42,
            color=ORANGE, label="ACP pondérée · 20 axes · log(taille)", zorder=3)
    axe.axhline(1.0, color=ENCRE, ls=":", lw=1.1, zorder=4)
    axe.text(len(dates) - 0.4, 1.06, "1 point", fontsize=8, color=ENCRE, ha="right")
    axe.set_xticks(x)
    axe.set_xticklabels(dates, rotation=90, fontsize=7.5, color=GRIS)
    axe.set_ylabel("erreur médiane à 25 % de dépouillement\n(points de %oui)",
                   fontsize=9, color=GRIS)
    axe.set_xlim(-0.8, len(dates) - 0.2)
    axe.legend(fontsize=9, frameon=False, loc="upper right")
    axe.grid(axis="y", color="#e3e1dc", lw=0.8, zorder=0)
    habiller(axe)
    axe.set_title("Les 30 votations du backtest, triées par difficulté — "
                  "le problème est la queue, pas le cas médian",
                  fontsize=11.5, color=ENCRE, loc="left")
    figure.tight_layout()
    for suffixe in ("png", "pdf"):
        figure.savefig(f"var/backtest/distribution_objets.{suffixe}", dpi=130,
                       facecolor=FOND)
    plt.close(figure)


def figure_leviers(resultats):
    """Ce que chaque levier fait a la mediane, a la queue et au pire cas."""
    dates = sorted(resultats)
    pires = sorted(dates, key=lambda d: -resultats[d]["u6"])[:6]
    mesures = [("médiane des 30 objets",
                lambda c: np.median([resultats[d][c] for d in dates])),
               ("médiane des 6 pires",
                lambda c: np.median([resultats[d][c] for d in pires])),
               ("le pire objet",
                lambda c: max(resultats[d][c] for d in dates))]
    figure, axes = plt.subplots(1, 3, figsize=(14.5, 4.9), facecolor=FOND)
    for axe, (titre, calcul) in zip(axes, mesures):
        valeurs = [calcul(cle) for cle, *_ in VARIANTES]
        y = np.arange(len(VARIANTES))[::-1]
        axe.barh(y, valeurs, height=0.7,
                 color=[c for *_, c in VARIANTES], zorder=3)
        for position, valeur in zip(y, valeurs):
            axe.text(valeur + max(valeurs) * 0.02, position, f"{valeur:.2f}",
                     va="center", fontsize=8.5, color=ENCRE, zorder=5)
        axe.set_yticks(y)
        axe.set_yticklabels([nom for _, nom, _ in VARIANTES] if axe is axes[0]
                            else [], fontsize=8.5, color=GRIS)
        axe.set_xlim(0, max(valeurs) * 1.18)
        axe.set_title(titre, fontsize=10, color=ENCRE, loc="left")
        axe.grid(axis="x", color="#e3e1dc", lw=0.8, zorder=0)
        habiller(axe)
    legende = [Patch(facecolor=BLEU, label="6 axes ACP"),
               Patch(facecolor=AQUA, label="6 axes + log(taille)"),
               Patch(facecolor=ORANGE, label="20 axes ACP"),
               Patch(facecolor=NEUTRE, label="sans extrapolation")]
    figure.legend(handles=legende, loc="lower center", ncol=4, frameon=False,
                  fontsize=9)
    figure.suptitle("Erreur à 25 % de dépouillement, en points de %oui — "
                    "les leviers ne se classent pas pareil selon le critère",
                    fontsize=11.5, color=ENCRE, x=0.012, ha="left")
    figure.tight_layout(rect=(0, 0.07, 1, 0.94))
    for suffixe in ("png", "pdf"):
        figure.savefig(f"var/backtest/leviers_outliers.{suffixe}", dpi=130,
                       facecolor=FOND)
    plt.close(figure)


resultats = calculer()
figure_distribution(resultats)
figure_leviers(resultats)
print("var/backtest/{distribution_objets,leviers_outliers}.{png,pdf}")
