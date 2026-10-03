from types import SimpleNamespace

import numpy as np
import pytest

from pca.management.commands.populate_pca import acp_ponderee, orienter_comme_avant


def test_peser_double_revient_a_compter_deux_fois():
    """Une commune de poids 2 tire les axes comme deux communes identiques."""
    alea = np.random.default_rng(0)
    X = alea.normal(size=(40, 10))
    poids = np.ones(40)
    poids[0] = 2

    ponderee = acp_ponderee(X, poids)
    dupliquee = acp_ponderee(np.vstack([X, X[:1]]), np.ones(41))[:40]

    assert np.abs(ponderee) == pytest.approx(np.abs(dupliquee))


def test_les_axes_gardent_l_orientation_du_calcul_precedent():
    """Un axe retourné par la SVD est remis dans le sens d'avant ; un axe qui
    n'existait pas encore garde le sien."""
    communes = [SimpleNamespace(id=i) for i in range(5)]
    avant = {i: [float(i), 1.0 - i] for i in range(5)}
    X = np.array([[-float(i), 1.0 - i, 7.0] for i in range(5)])

    X = orienter_comme_avant(X, communes, avant)

    assert X[:, 0] == pytest.approx([0, 1, 2, 3, 4])
    assert X[:, 1] == pytest.approx([1, 0, -1, -2, -3])
    assert X[:, 2] == pytest.approx([7] * 5)
