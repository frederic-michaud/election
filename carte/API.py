"""Entrée historique des cartes. La figure elle-même vit dans `carte/figure.py`.

Les vues et le reste du site passent par ici ; le rendu, les couleurs et la
projection sont l'affaire de la voie Interface, un cran plus bas.
"""

from carte.figure import carte
from scrutin.graphiques import en_div


def generate_carte_plot(communes):
    """``communes`` : le dict ``sujet["communes"]`` du contrat de vue."""
    return en_div(carte(communes))
