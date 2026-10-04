"""La calibration de la fourchette, sur des historiques synthétiques."""

import numpy as np
import pytest

from scrutin.donnees import demi_fourchette
from scrutin.management.commands.calibrer_fourchette import AVANCES, ecarts, table


def historique(bruit, nb_communes=400, nb_objets=30, graine=0):
    """oui, non, inscrits, bulletins : chaque vote est affine en deux profils latents."""
    alea = np.random.default_rng(graine)
    profils = alea.normal(size=(nb_communes, 2))
    pentes = alea.normal(0, 0.08, size=(2, nb_objets))
    part_oui = np.clip(0.5 + profils @ pentes + alea.normal(0, bruit, (nb_communes, nb_objets)), 0.05, 0.95)
    inscrits = np.repeat(alea.integers(200, 50_000, nb_communes)[:, None], nb_objets, axis=1).astype(float)
    bulletins = np.round(0.45 * inscrits)
    oui = np.round(part_oui * bulletins)
    return oui, bulletins - oui, inscrits, bulletins


def test_sans_bruit_la_projection_est_exacte_et_la_fourchette_nulle():
    """Les votes sont exactement dans l'espace des axes : la projection retrouve
    le résultat final à l'arrondi des voix près, quelle que soit l'avance."""
    resultat = ecarts(*historique(bruit=0.0), tirages=3, min_anterieurs=20)
    assert all(max(e) < 1e-3 for e in resultat.values() if e)


def test_avec_du_bruit_la_fourchette_se_resserre_avec_le_depouillement():
    lignes = table(ecarts(*historique(bruit=0.03), tirages=5, min_anterieurs=20))
    largeurs = dict(lignes)
    assert largeurs[0.05] > largeurs[0.5] > largeurs[0.95] > 0
    assert lignes[-1] == (1.0, 0.0)
    assert {avance for avance, _ in lignes} <= set(AVANCES) | {1.0}


def test_la_vue_interpole_la_table_et_s_abstient_sans_elle():
    table_ = [(0.1, 0.02), (0.5, 0.01), (1.0, 0.0)]
    assert demi_fourchette(0.3, table_) == pytest.approx(0.015)
    assert demi_fourchette(0.01, table_) == pytest.approx(0.02)
    assert demi_fourchette(0.3, []) is None
