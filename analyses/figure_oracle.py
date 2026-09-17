"""Bar plot des six pires votations a 25 %, avec la borne d'oracle.

La derniere barre calcule l'ACP en incluant l'objet du jour : c'est une fuite
assumee, donc une borne superieure — « jusqu'ou irait-on si l'ACP avait deja
les bons axes ». Elle n'est pas atteignable le jour J, d'ou la hachure.
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
BLEU, ORANGE, AQUA, NEUTRE = "#2a78d6", "#eb6834", "#1baf7a", "#52514e"
BARRES = [
    ("u6", "ACP uniforme · 6 axes  (production)", BLEU, None),
    ("p6", "ACP pondérée · 6 axes", BLEU, None),
    ("u6c", "ACP uniforme · 6 axes · canton", BLEU, None),
    ("u6t", "ACP uniforme · 6 axes · taille", BLEU, None),
    ("u20", "ACP uniforme · 20 axes", ORANGE, None),
    ("p20t", "ACP pondérée · 20 axes · taille", ORANGE, None),
    ("fuite", "ACP 6 axes incluant l'objet du jour", AQUA, "///"),
    ("nu", "dépouillement nu", NEUTRE, None),
]


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

    sortie = {}
    for cible in choisir_cibles(sujets, 20, 4, lambda m: None):
        indice = cible[0]
        date = sujets[indice][2]
        if date not in PIRES:
            continue
        ant = [j for j, s in enumerate(sujets) if s[2] < date]
        so, sn = oui[:, ant], non[:, ant]
        valide = ~np.isnan(so).any(axis=1) & ~np.isnan(sn).any(axis=1)
        garde = valide & ~np.isnan(oui[:, indice]) & ~np.isnan(non[:, indice]) \
            & (elec[:, indice] > 0) & (bul[:, indice] > 0)
        matrice = so[valide] / (so[valide] + sn[valide])
        taille_hist = np.maximum(np.nanmean(
            np.nan_to_num(bul[valide][:, ant], nan=0.0), axis=1), 1.0)
        comp_u = acp(matrice, np.ones(len(matrice)), 20)[garde[valide]]
        comp_p = acp(matrice, taille_hist, 20)[garde[valide]]

        # Fuite assumee : l'objet du jour entre dans la matrice de l'ACP.
        colonnes = ant + [indice]
        mo, mn = oui[garde][:, colonnes], non[garde][:, colonnes]
        comp_f = acp(mo / (mo + mn), np.ones(int(garde.sum())), 6)

        canton = canton_tous[garde]
        codes = np.unique(canton)
        indic = (canton[:, None] == codes[None, :]).astype(float)

        precedent = max(ant, key=lambda j: sujets[j][2])
        expr = oui[garde, indice] + non[garde, indice]
        pct, part = oui[garde, indice] / expr, expr / elec[garde, indice]
        bulletins, elec_prec = bul[garde, indice], elec[garde, precedent]
        oui_abs, nb = oui[garde, indice], int(garde.sum())
        vrai = oui_abs.sum() / expr.sum()
        lt = np.log10(np.maximum(elec_prec, 1.0))
        lt = ((lt - lt.mean()) / lt.std())[:, None]
        un = np.ones((nb, 1))

        designs = {
            "u6": np.column_stack([comp_u[:, :6], un]),
            "p6": np.column_stack([comp_p[:, :6], un]),
            "u6c": np.column_stack([comp_u[:, :6], indic, un]),
            "u6t": np.column_stack([comp_u[:, :6], lt, un]),
            "u20": np.column_stack([comp_u, un]),
            "p20t": np.column_stack([comp_p, lt, un]),
            "fuite": np.column_stack([comp_f, un]),
        }

        rng = np.random.default_rng(2024 + sujets[indice][1])
        proj = {c: [] for c in designs}
        nus = []
        for _ in range(TIRAGES):
            ordre = ordres("realiste", pct, comp_u[:, :6], elec[garde, indice], rng)
            cumul = np.cumsum(expr[ordre])
            k = max(int(np.searchsorted(cumul, AVANCE * cumul[-1]) + 1), 8)
            dedans, hors = ordre[:k], ordre[k:]
            w = bulletins[dedans].astype(float)
            nus.append(oui_abs[dedans].sum() / expr[dedans].sum())
            for cle, design in designs.items():
                b_oui = ajuster(design[dedans], pct[dedans], w)
                b_part = ajuster(design[dedans], part[dedans], w)
                votants = (design[hors] @ b_part) * elec_prec[hors]
                proj[cle].append((oui_abs[dedans].sum()
                                  + ((design[hors] @ b_oui) * votants).sum())
                                 / (expr[dedans].sum() + votants.sum()))
        sortie[date] = {"vrai": 100 * vrai, "nu": 100 * float(np.median(nus)),
                        **{c: 100 * float(np.median(proj[c])) for c in designs}}
        print(f"  {date} ok", flush=True)
    return sortie


def tracer(donnees):
    figure, axes = plt.subplots(2, 3, figsize=(16.5, 9.2))
    figure.patch.set_facecolor("#fcfcfb")
    for axe, (date, libelle) in zip(np.ravel(axes), PIRES.items()):
        d = donnees[date]
        vrai = d["vrai"]
        valeurs = [d[cle] - vrai for cle, *_ in BARRES]
        y = np.arange(len(BARRES))[::-1]
        for position, (cle, _, couleur, hachure), valeur in zip(y, BARRES, valeurs):
            axe.barh(position, valeur, height=0.72, color=couleur, zorder=3,
                     hatch=hachure, edgecolor="#fcfcfb" if hachure else "none",
                     linewidth=0)
            decalage = 0.09 if valeur >= 0 else -0.09
            axe.text(valeur + decalage, position, f"{d[cle]:.2f}", va="center",
                     ha="left" if valeur >= 0 else "right", fontsize=8.5,
                     color="#0b0b0b", zorder=5)
        axe.axvline(0, color="#0b0b0b", lw=1.4, zorder=4)
        axe.set_yticks(y)
        axe.set_yticklabels([nom for _, nom, *_ in BARRES], fontsize=8.5,
                            color="#52514e")
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
               Patch(facecolor=AQUA, hatch="///", edgecolor="#fcfcfb",
                     label="oracle : ACP incluant l'objet du jour (non atteignable)"),
               Patch(facecolor=NEUTRE, label="dépouillement nu"),
               Line2D([], [], color="#0b0b0b", lw=1.4, label="résultat final")]
    figure.legend(handles=legende, loc="lower center", ncol=5, frameon=False,
                  fontsize=9.5, bbox_to_anchor=(0.5, 0.005))
    figure.suptitle("Projection à 25 % de dépouillement — les six votations les "
                    "plus mal projetées\nécart au résultat final, en points de "
                    "%oui ; étiquette = %oui projeté (médiane sur 15 ordres "
                    "d'arrivée)", fontsize=12, ha="left", x=0.045, y=0.985)
    figure.tight_layout(rect=(0, 0.035, 1, 0.93))
    for suffixe in ("png", "pdf"):
        figure.savefig(f"var/backtest/oracle_six_pires.{suffixe}", dpi=130,
                       facecolor="#fcfcfb")
    moyennes = {cle: np.median([abs(donnees[d][cle] - donnees[d]["vrai"])
                                for d in PIRES]) for cle, *_ in BARRES}
    print("\nmédiane des 6 pires :")
    for cle, nom, *_ in BARRES:
        print(f"  {nom:<40} {moyennes[cle]:.3f}")


tracer(calculer())
