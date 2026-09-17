"""Les typologies OFS non exploitees expliquent-elles les residus du modele ?

Le CSV `data/agvch_niveaux_*.csv` porte 29 colonnes ; on n'en importe que deux
(langue, degre d'urbanisation). Les autres sont des typologies officielles
— type de commune, ville/campagne, montagne, agglomeration, bassin d'emploi.

Question : apportent-elles quelque chose que les 6 composantes de l'ACP, qui
resument deja 55+ votations, n'ont pas ? On ajuste le modele de production sur
*toutes* les communes, puis on regarde quelle part de la variance des residus
chaque typologie explique. Controle par permutation : une variable a 25 classes
explique mecaniquement plus qu'une variable a 2 classes, meme au hasard.

    .venv/bin/python var/meta_communes.py
"""
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

from scrutin.management.commands.backtest_ordre_depouillement import (  # noqa: E402
    Command,
    ajuster,
    charger,
    choisir_cibles,
)

BASE = "var/backtest/snapshot.sqlite3"
CSV = "data/agvch_niveaux_2026-01-01.csv"
IGNORE = {"HistoricalCode", "BfsCode", "Name", "Canton", "District"}


def part_expliquee(valeurs, residus, poids):
    """Part de la variance ponderee des residus captee par les moyennes de groupe."""
    total = (poids * residus**2).sum()
    if total <= 0:
        return np.nan
    inter = 0.0
    for v in np.unique(valeurs):
        m = valeurs == v
        if m.sum() >= 3:
            w = poids[m]
            inter += w.sum() * ((w * residus[m]).sum() / w.sum()) ** 2
    return inter / total


def main():
    commande = Command()
    commande.nb_composantes = 6
    commande.seuil = 7
    sujets, communes, oui, non, elec, bul = charger(BASE)

    conn = sqlite3.connect(f"file:{BASE}?mode=ro&immutable=1", uri=True)
    ofs = dict(conn.execute("select id, numero_ofs from scrutin_commune"))
    conn.close()
    table = pd.read_csv(CSV).set_index("BfsCode")
    colonnes = [c for c in table.columns if c not in IGNORE]
    par_commune = {c: np.array([table[c].get(ofs.get(cid), np.nan)
                                for cid, _ in communes]) for c in colonnes}

    cibles = choisir_cibles(sujets, 20, 4, lambda m: None)
    cumul = {c: [] for c in colonnes}
    cumul_hasard = {c: [] for c in colonnes}
    cache = {}
    rng = np.random.default_rng(0)
    for rang, cible in enumerate(cibles, 1):
        ctx = commande.contexte(cible, sujets, oui, non, elec, bul, cache)
        indice = cible[0]
        valide, _ = cache[sujets[indice][2]]
        garde = valide & ~np.isnan(oui[:, indice]) & ~np.isnan(non[:, indice]) \
            & (elec[:, indice] > 0) & (bul[:, indice] > 0)

        design = np.column_stack([ctx["composantes"], np.ones(ctx["nb_communes"])])
        poids = ctx["bulletins"].astype(float)
        beta = ajuster(design, ctx["pourcentage_oui"], poids)
        residus = ctx["pourcentage_oui"] - design @ beta

        for c in colonnes:
            v = par_commune[c][garde]
            ok = ~pd.isna(v)
            if ok.sum() < 100:
                continue
            cumul[c].append(part_expliquee(v[ok], residus[ok], poids[ok]))
            cumul_hasard[c].append(part_expliquee(rng.permutation(v[ok]),
                                                  residus[ok], poids[ok]))
        print(f"  [{rang}/{len(cibles)}] {ctx['date']}", flush=True)

    print(f"\nPart de la variance des residus expliquee, mediane sur {len(cibles)} objets")
    print("(residus du modele de production ajuste sur toutes les communes)\n")
    print(f"{'variable':>16} {'classes':>8} {'reelle':>9} {'hasard':>9} {'gain':>9}")
    print("-" * 56)
    lignes = []
    for c in colonnes:
        if not cumul[c]:
            continue
        reelle = np.nanmedian(cumul[c])
        hasard = np.nanmedian(cumul_hasard[c])
        lignes.append((reelle - hasard, c, int(np.nanmax([len(np.unique(
            par_commune[c][~pd.isna(par_commune[c])]))])), reelle, hasard))
    for gain, c, n, reelle, hasard in sorted(lignes, reverse=True):
        print(f"{c:>16} {n:>8} {reelle:>8.1%} {hasard:>8.1%} {gain:>8.1%}")


main()
