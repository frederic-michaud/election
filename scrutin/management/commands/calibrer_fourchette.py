"""Fourchette de la projection, calibrée en rejouant les votations passées.

Pour chaque objet précédé d'au moins ``--min-anterieurs`` votations, on refait
l'ACP sur les seuls objets antérieurs, on simule des soirées de dépouillement
et on note, à chaque avance, l'écart entre la projection et le résultat final.
La demi-largeur retenue est l'écart que 95 % des projections ne dépassent pas
(doc/backtest.md).

À relancer après chaque ``populate_pca`` : la fourchette suit le modèle et
l'historique.
"""

import numpy as np
from django.core.management.base import BaseCommand
from django.db import transaction

from pca.management.commands.populate_pca import acp_ponderee
from scrutin.extrapolation import SEUIL_COMMUNES
from scrutin.models import Fourchette, ResultatCommunalHistorique

AVANCES = (0.003, 0.005, 0.0075, 0.01, 0.02, 0.03, 0.05, 0.10, 0.15, 0.20, 0.25,
           0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 0.95)
COUVERTURE = 0.95
# Ordre d'arrivée simulé : les petites communes d'abord, avec du hasard
# (retard = pente · log10(électeurs) + bruit).
RETARD_PENTE, RETARD_BRUIT = 80.0, 46.0


def matrices():
    """oui, non, inscrits, bulletins : communes × objets, objets par date ; NaN si absent."""
    lignes = list(ResultatCommunalHistorique.objects.values_list(
        'commune_id', 'sujet_vote__date', 'sujet_vote_id',
        'nombre_oui', 'nombre_non', 'electeurs_inscrits', 'bulletins_rentres'))
    communes = {c: i for i, c in enumerate(sorted({ligne[0] for ligne in lignes}))}
    objets = {s: j for j, (_, s) in enumerate(sorted({(ligne[1], ligne[2]) for ligne in lignes}))}
    tableaux = np.full((4, len(communes), len(objets)), np.nan)
    for commune, _, objet, *valeurs in lignes:
        tableaux[:, communes[commune], objets[objet]] = valeurs
    return tableaux


def projeter(design, depouillees, oui, participation, exprimes, bulletins, electeurs):
    """La projection de production (scrutin/extrapolation.py), en forme close."""
    racine = np.sqrt(bulletins[depouillees])
    systeme = design[depouillees] * racine[:, None]
    beta_oui = np.linalg.lstsq(systeme, oui[depouillees] * racine, rcond=None)[0]
    beta_part = np.linalg.lstsq(systeme, participation[depouillees] * racine, rcond=None)[0]
    manquantes = ~depouillees
    votants = (design[manquantes] @ beta_part) * electeurs[manquantes]
    oui_final = (oui[depouillees] * exprimes[depouillees]).sum() + ((design[manquantes] @ beta_oui) * votants).sum()
    return oui_final / (exprimes[depouillees].sum() + votants.sum())


def ecarts(oui, non, inscrits, bulletins, tirages, min_anterieurs, graine=0):
    """{avance: [écart absolu entre projection et résultat final, …]}, en part de oui."""
    alea = np.random.default_rng(graine)
    with np.errstate(invalid='ignore', divide='ignore'):
        part_oui = oui / (oui + non)
    resultat = {avance: [] for avance in AVANCES}
    for cible in range(min_anterieurs, oui.shape[1]):
        complet = ~np.isnan(part_oui[:, :cible + 1]).any(axis=1) & (inscrits[:, cible] > 0)
        electeurs = inscrits[complet, cible - 1]
        axes = acp_ponderee(part_oui[complet, :cible], electeurs)
        design = np.column_stack([axes, np.ones(len(axes))])
        exprimes = oui[complet, cible] + non[complet, cible]
        participation = bulletins[complet, cible] / inscrits[complet, cible]
        vrai = oui[complet, cible].sum() / exprimes.sum()
        for _ in range(tirages):
            retard = (RETARD_PENTE * np.log10(np.maximum(inscrits[complet, cible], 1))
                      + alea.normal(0, RETARD_BRUIT, len(design)))
            ordre = np.argsort(retard)
            part_cumulee = np.cumsum(exprimes[ordre]) / exprimes.sum()
            for avance in AVANCES:
                depouillees = np.zeros(len(design), bool)
                depouillees[ordre[:np.searchsorted(part_cumulee, avance) + 1]] = True
                if depouillees.sum() < SEUIL_COMMUNES:
                    continue
                projection = projeter(design, depouillees, part_oui[complet, cible], participation,
                                      exprimes, bulletins[complet, cible], electeurs)
                resultat[avance].append(abs(projection - vrai))
    return resultat


def table(ecarts_par_avance):
    """[(avance, demi-largeur)], fermée par (1, 0) : tout dépouillé, plus d'incertitude."""
    lignes = [(avance, float(np.quantile(e, COUVERTURE)))
              for avance, e in ecarts_par_avance.items() if e]
    return lignes + [(1.0, 0.0)]


class Command(BaseCommand):
    help = "Rejoue les votations passées → Fourchette. Remplace toute la table."

    def add_arguments(self, parser):
        parser.add_argument("--tirages", type=int, default=50,
                            help="soirées simulées par objet")
        parser.add_argument("--min-anterieurs", type=int, default=40,
                            help="votations antérieures exigées pour rejouer un objet")

    def handle(self, *args, **options):
        oui, non, inscrits, bulletins = matrices()
        if oui.shape[1] <= options["min_anterieurs"]:
            self.stderr.write(f"{oui.shape[1]} objets dans l'historique : trop peu pour calibrer, "
                              "table inchangée")
            return
        lignes = table(ecarts(oui, non, inscrits, bulletins,
                              options["tirages"], options["min_anterieurs"]))
        with transaction.atomic():
            Fourchette.objects.all().delete()
            Fourchette.objects.bulk_create(Fourchette(avance=a, demi_largeur=d) for a, d in lignes)
        objets = oui.shape[1] - options["min_anterieurs"]
        self.stdout.write(f"{objets} objets × {options['tirages']} soirées simulées")
        for avance, demi in lignes:
            self.stdout.write(f"  {100 * avance:5.1f} %  ±{100 * demi:.2f} points")
