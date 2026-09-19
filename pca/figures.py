"""Les deux nuages ACP en Plotly, à partir du contrat de vue (aucun ORM)."""

import re

import plotly.graph_objects as go

from scrutin import charte

SEUIL_NOMS = 15      # en dessous, la recherche écrit les noms (« Lau » en trouve 13)
LARGEUR_ETIQUETTE = 30
NB_REPLI = 8         # points nommés si aucun de ceux ci-dessous n'est dans la base

# Nommés d'office : des points connus qui couvrent le plan des deux premiers axes.
COMMUNES_PAR_DEFAUT = [
    261,    # Zürich
    6621,   # Genève
    5586,   # Lausanne
    351,    # Bern
    2701,   # Basel
    5192,   # Lugano
    6266,   # Sion
    1711,   # Zug
    3101,   # Appenzell
    576,    # Grindelwald
]
# Par numéro fédéral, avec le nom d'usage : l'intitulé officiel ne dit souvent rien.
OBJETS_PAR_DEFAUT = {
    6310: "Initiative de limitation",
    6380: "Interdiction du voile intégral",
    6170: "No Billag",
    6350: "Avions de combat",
    6600: "AVS 21",
    6470: "Mariage pour tous",
    6440: "Loi sur le CO2",
    6360: "Multinationales responsables",
    6650: "13e rente AVS",
}


def _etiquette(nom):
    """Nom court d'un objet : son nom d'usage entre parenthèses, sinon le texte
    entre guillemets, tronqué. Les intitulés officiels font ~100 signes."""
    entre_parentheses = re.findall(r"\(([^()]{3,})\)", nom)
    entre_guillemets = re.findall(r"«\s*(.+?)\s*»", nom)
    court = (entre_parentheses or entre_guillemets or [nom])[-1]
    return court if len(court) <= LARGEUR_ETIQUETTE else court[:LARGEUR_ETIQUETTE - 1] + "…"


def _trace_base(donnees):
    return go.Scattergl(
        x=donnees["axes"][0], y=donnees["axes"][1],
        mode="markers",
        marker={"size": 5, "color": charte.POINT, "opacity": 0.55},
        hovertext=donnees["survol"],
        hovertemplate="%{hovertext}<extra></extra>",
    )


def _trace_etiquettes(couleur, taille):
    """Trace vide, remplie par ``nuage.js``."""
    return go.Scattergl(
        x=[], y=[], text=[],
        mode="markers+text",
        marker={"size": taille, "color": couleur},
        textposition="bottom center",
        textfont={"size": 11, "color": couleur},
        hovertext=[], hovertemplate="%{hovertext}<extra></extra>",
    )


def _trace_anneau():
    """Le point survolé sur une carte ou dans la bulle du clic."""
    return go.Scattergl(
        x=[], y=[], mode="markers", hoverinfo="skip",
        marker={"size": 15, "symbol": "circle-open", "color": charte.ENCRE, "line": {"width": 2}},
    )


def _selection(donnees, objets):
    """Indices des points nommés d'office."""
    voulus = list(OBJETS_PAR_DEFAUT) if objets else COMMUNES_PAR_DEFAUT
    rang = {cle: i for i, cle in enumerate(donnees["cles"])}
    trouves = [rang[cle] for cle in voulus if cle in rang]
    if trouves:
        return trouves
    x, y = donnees["axes"][0], donnees["axes"][1]
    return sorted(range(len(x)), key=lambda i: -(x[i] ** 2 + y[i] ** 2))[:NB_REPLI]


def figure_nuage(donnees, objets=False):
    """Nuage dans le plan des deux premiers axes ; les six sont dans ``meta``.
    ``objets`` : le cercle des corrélations, cadré sur le cercle unité."""
    figure = go.Figure([
        _trace_base(donnees),
        _trace_etiquettes(charte.ENCRE, 7),     # points nommés
        _trace_etiquettes(charte.ROUGE, 9),     # résultats de la recherche
        _trace_anneau(),
    ])
    charte.habiller_nuage(figure, "Axe 1", "Axe 2")
    etiquettes = donnees["noms"]
    if objets:
        figure.update_layout(
            xaxis={"range": [-1.08, 1.08]},
            yaxis={"range": [-1.08, 1.08], "scaleanchor": "x"},
            shapes=[{"type": "circle", "x0": -1, "y0": -1, "x1": 1, "y1": 1,
                     "line": {"color": charte.GRILLE, "width": 1}}],
        )
        etiquettes = [OBJETS_PAR_DEFAUT.get(cle) or _etiquette(nom)
                      for cle, nom in zip(donnees["cles"], donnees["noms"])]
    figure.update_layout(meta={"nuage": {
        "noms": donnees["noms"],
        "cles": donnees["cles"],
        "etiquettes": etiquettes,
        "survol": donnees["survol"],
        "axes": [[round(v, 3) for v in axe] for axe in donnees["axes"]],
        "selection": _selection(donnees, objets),
        "seuil_noms": SEUIL_NOMS,
        "fixe": bool(objets),
    }})
    return figure
