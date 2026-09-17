"""Les deux nuages ACP en Plotly, à partir du contrat de vue (aucun ORM)."""

import re

import plotly.graph_objects as go

from scrutin import charte

NB_EXTREMES = 8      # objets étiquetés d'office : ceux qui définissent le plan
SEUIL_NOMS = 15      # en dessous, la recherche écrit les noms sous les points
                     # (« Lau » en allume 13 : le seuil doit passer cet exemple-là)
LARGEUR_ETIQUETTE = 30


def _etiquette(nom):
    """Nom court d'un objet, pour l'écrire à côté d'un point.

    Les intitulés officiels font 98 signes en médiane — « Initiative populaire
    « Pour une économie responsable respectant les limites planétaires
    (initiative pour la responsabilité environnementale) » ». Mais ils se
    terminent presque toujours par leur nom d'usage entre parenthèses : c'est
    lui qu'on garde, faute de quoi toutes les étiquettes commenceraient par les
    mêmes vingt signes.
    """
    entre_parentheses = re.findall(r"\(([^()]{3,})\)", nom)
    entre_guillemets = re.findall(r"«\s*(.+?)\s*»", nom)
    if entre_parentheses:
        court = entre_parentheses[-1]
    elif entre_guillemets:
        # Les initiatives d'avant l'usage du nom court : « Halte à la
        # surpopulation… » vaut mieux que trente signes de « Initiative populaire ».
        court = entre_guillemets[-1]
    else:
        court = nom
    return court if len(court) <= LARGEUR_ETIQUETTE else court[:LARGEUR_ETIQUETTE - 1] + "…"


def _trace_base(donnees):
    """Tous les points, au repos."""
    return go.Scattergl(
        x=donnees["axes"][0], y=donnees["axes"][1],
        mode="markers",
        marker={"size": 5, "color": charte.POINT, "opacity": 0.55},
        hovertext=donnees["survol"],
        hovertemplate="%{hovertext}<extra></extra>",
    )


def _trace_etiquettes(couleur, taille):
    """Trace vide que ``nuage.js`` remplit : extrêmes d'office, ou recherche."""
    return go.Scattergl(
        x=[], y=[], text=[],
        mode="markers+text",
        marker={"size": taille, "color": couleur},
        textposition="bottom center",
        textfont={"size": 11, "color": couleur},
        hovertext=[], hovertemplate="%{hovertext}<extra></extra>",
    )


def figure_nuage(donnees, objets=False):
    """Nuage dans le plan de deux axes, les six coordonnées rangées dans ``meta``.

    ``objets`` : c'est le cercle des corrélations, donc cadré sur le cercle
    unité, étiqueté d'office sur les points les plus excentrés, et avec des
    intitulés raccourcis.
    """
    figure = go.Figure([
        _trace_base(donnees),
        _trace_etiquettes(charte.ENCRE, 6),     # extrêmes, seulement pour les objets
        _trace_etiquettes(charte.ROUGE, 9),     # résultats de la recherche
    ])
    charte.habiller_nuage(figure, "Axe 1", "Axe 2")
    if objets:
        figure.update_layout(
            xaxis={"range": [-1.08, 1.08]},
            yaxis={"range": [-1.08, 1.08], "scaleanchor": "x"},
            shapes=[{"type": "circle", "x0": -1, "y0": -1, "x1": 1, "y1": 1,
                     "line": {"color": charte.GRILLE, "width": 1}}],
        )
    figure.update_layout(meta={"nuage": {
        "noms": donnees["noms"],
        "etiquettes": [_etiquette(nom) for nom in donnees["noms"]] if objets else donnees["noms"],
        "survol": donnees["survol"],
        "axes": [[round(v, 3) for v in axe] for axe in donnees["axes"]],
        "extremes": NB_EXTREMES if objets else 0,
        "seuil_noms": SEUIL_NOMS,
        "fixe": bool(objets),
    }})
    return figure
