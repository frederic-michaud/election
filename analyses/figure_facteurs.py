"""Bar plot des 8 variantes sur les six votations les plus ratees, a 25 %.

Memes calculs et meme graine que var/facteurs.py : on ressort les %oui signes
au lieu des erreurs absolues, pour pouvoir les situer face au resultat final.
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

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

from scrutin.management.commands.backtest_ordre_depouillement import (  # noqa: E402
    ajuster,
    charger,
    choisir_cibles,
    ordres,
)

BASE = "var/backtest/snapshot.sqlite3"
AVANCE, TIRAGES = 0.25, 15
PIRES = {"2025-09-28": "Impôt immobilier",
         "2020-02-09": "Logements abordables",
         "2018-11-25": "Vaches à cornes",
         "2022-02-13": "Expérimentation animale",
         "2021-09-26": "Impôts sur les salaires",
         "2021-03-07": "Dissimulation du visage"}
BLEU, ORANGE, NEUTRE = "#2a78d6", "#eb6834", "#52514e"


def acp(matrice, poids, k):
    w = poids / poids.sum()
    centre = matrice - (matrice * w[:, None]).sum(axis=0)
    _, _, vt = np.linalg.svd(centre * np.sqrt(w)[:, None], full_matrices=False)
    return centre @ vt[:k].T


def calculer():
    sujets, communes, oui, non, elec, bul = charger(BASE)
    conn = sqlite3.connect(f"file:{BASE}?mode=ro&immutable=1", uri=True)
    cantons_id = dict(conn.execute("select id, canton_id from scrutin_commune"))
    conn.close()
    canton_tous = np.array([cantons_id.get(cid, -1) for cid, _ in communes])
    variantes = [(p, k, c) for p in (False, True) for k in (6, 20)
                 for c in (False, True)]

    sortie = {}
    for cible in choisir_cibles(sujets, 20, 4, lambda m: None):
        indice = cible[0]
        date = sujets[indice][2]
        if date not in PIRES:
            continue
        anterieurs = [j for j, s in enumerate(sujets) if s[2] < date]
        so, sn = oui[:, anterieurs], non[:, anterieurs]
        valide = ~np.isnan(so).any(axis=1) & ~np.isnan(sn).any(axis=1)
        garde = valide & ~np.isnan(oui[:, indice]) & ~np.isnan(non[:, indice]) \
            & (elec[:, indice] > 0) & (bul[:, indice] > 0)
        matrice = so[valide] / (so[valide] + sn[valide])
        taille = np.maximum(np.nanmean(np.nan_to_num(bul[valide][:, anterieurs],
                                                     nan=0.0), axis=1), 1.0)
        comp = {False: acp(matrice, np.ones(len(matrice)), 20)[garde[valide]],
                True: acp(matrice, taille, 20)[garde[valide]]}
        canton = canton_tous[garde]
        codes = np.unique(canton)
        indic = (canton[:, None] == codes[None, :]).astype(float)

        precedent = max(anterieurs, key=lambda j: sujets[j][2])
        expr = oui[garde, indice] + non[garde, indice]
        pct, part = oui[garde, indice] / expr, expr / elec[garde, indice]
        bulletins, elec_prec = bul[garde, indice], elec[garde, precedent]
        oui_abs, nb = oui[garde, indice], int(garde.sum())
        vrai = oui_abs.sum() / expr.sum()

        designs = {}
        for v in variantes:
            pondere, k, avec = v
            bloc = [comp[pondere][:, :k]]
            if avec:
                bloc.append(indic)
            bloc.append(np.ones((nb, 1)))
            designs[v] = np.column_stack(bloc)

        rng = np.random.default_rng(2024 + sujets[indice][1])
        proj = {v: [] for v in variantes}
        nus = []
        for _ in range(TIRAGES):
            ordre = ordres("realiste", pct, comp[False][:, :6],
                           elec[garde, indice], rng)
            cumul = np.cumsum(expr[ordre])
            k_com = max(int(np.searchsorted(cumul, AVANCE * cumul[-1]) + 1), 8)
            dedans, hors = ordre[:k_com], ordre[k_com:]
            w = bulletins[dedans].astype(float)
            nus.append(oui_abs[dedans].sum() / expr[dedans].sum())
            for v in variantes:
                design = designs[v]
                b_oui = ajuster(design[dedans], pct[dedans], w)
                b_part = ajuster(design[dedans], part[dedans], w)
                votants = (design[hors] @ b_part) * elec_prec[hors]
                proj[v].append((oui_abs[dedans].sum()
                                + ((design[hors] @ b_oui) * votants).sum())
                               / (expr[dedans].sum() + votants.sum()))
        sortie[date] = {"vrai": 100 * vrai,
                        "nu": 100 * float(np.median(nus)),
                        **{v: 100 * float(np.median(proj[v])) for v in variantes}}
        print(f"  {date} ok", flush=True)
    return variantes, sortie


def tracer(variantes, donnees):
    noms = {(False, 6, False): "ACP uniforme · 6 axes",
            (False, 6, True): "ACP uniforme · 6 axes · canton",
            (False, 20, False): "ACP uniforme · 20 axes",
            (False, 20, True): "ACP uniforme · 20 axes · canton",
            (True, 6, False): "ACP pondérée · 6 axes",
            (True, 6, True): "ACP pondérée · 6 axes · canton",
            (True, 20, False): "ACP pondérée · 20 axes",
            (True, 20, True): "ACP pondérée · 20 axes · canton"}
    ordre_barres = list(variantes) + ["nu"]
    figure, axes = plt.subplots(2, 3, figsize=(16.5, 9.2))
    figure.patch.set_facecolor("#fcfcfb")

    for axe, (date, libelle) in zip(np.ravel(axes), PIRES.items()):
        d = donnees[date]
        vrai = d["vrai"]
        valeurs = [d[v] - vrai for v in ordre_barres]
        couleurs = [NEUTRE if v == "nu" else (ORANGE if v[1] == 20 else BLEU)
                    for v in ordre_barres]
        y = np.arange(len(ordre_barres))[::-1]
        axe.barh(y, valeurs, height=0.72, color=couleurs, zorder=3)
        axe.axvline(0, color="#0b0b0b", lw=1.4, zorder=4)

        for position, variante, valeur in zip(y, ordre_barres, valeurs):
            decalage = 0.09 if valeur >= 0 else -0.09
            axe.text(valeur + decalage, position,
                     f"{d[variante]:.2f}", va="center",
                     ha="left" if valeur >= 0 else "right",
                     fontsize=8.5, color="#0b0b0b", zorder=5)
        axe.set_yticks(y)
        axe.set_yticklabels([noms.get(v, "dépouillement nu") for v in ordre_barres],
                            fontsize=8.5, color="#52514e")
        limite = max(1.0, max(abs(v) for v in valeurs) * 1.32)
        axe.set_xlim(-limite, limite)
        axe.set_title(f"{libelle}  ·  {date}\nrésultat final {vrai:.2f} % de oui",
                      fontsize=10, color="#0b0b0b", loc="left")
        axe.set_facecolor("#fcfcfb")
        axe.grid(axis="x", color="#e3e1dc", lw=0.8, zorder=0)
        axe.set_axisbelow(True)
        for cote in ("top", "right", "left"):
            axe.spines[cote].set_visible(False)
        axe.spines["bottom"].set_color("#c9c6bf")
        axe.tick_params(axis="x", labelsize=8, colors="#52514e")

    legende = [Patch(facecolor=BLEU, label="6 axes ACP"),
               Patch(facecolor=ORANGE, label="20 axes ACP"),
               Patch(facecolor=NEUTRE, label="dépouillement nu (sans extrapolation)"),
               Line2D([], [], color="#0b0b0b", lw=1.4, label="résultat final")]
    figure.legend(handles=legende, loc="lower center", ncol=4, frameon=False,
                  fontsize=9.5, bbox_to_anchor=(0.5, 0.005))
    figure.suptitle("Projection à 25 % de dépouillement — les six votations les "
                    "plus mal projetées\nécart au résultat final, en points de "
                    "%oui ; étiquette = %oui projeté (médiane sur 15 ordres "
                    "d'arrivée)", fontsize=12, ha="left", x=0.045, y=0.985)
    figure.tight_layout(rect=(0, 0.035, 1, 0.93))
    for suffixe in ("png", "pdf"):
        figure.savefig(f"var/backtest/facteurs_six_pires.{suffixe}", dpi=130,
                       facecolor="#fcfcfb")
    print("var/backtest/facteurs_six_pires.{png,pdf}")


variantes, donnees = calculer()
tracer(variantes, donnees)
