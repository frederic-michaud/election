import numpy as np
import pytest

from pca.management.commands.populate_pca import acp_ponderee


def test_peser_double_revient_a_compter_deux_fois():
    """Une commune de poids 2 tire les axes comme deux communes identiques."""
    alea = np.random.default_rng(0)
    X = alea.normal(size=(40, 10))
    poids = np.ones(40)
    poids[0] = 2

    ponderee = acp_ponderee(X, poids)
    dupliquee = acp_ponderee(np.vstack([X, X[:1]]), np.ones(41))[:40]

    assert np.abs(ponderee) == pytest.approx(np.abs(dupliquee))
