"""Palette et réglages Plotly, repris de la maquette D′ (couleurs aussi dans style.css)."""

from django.templatetags.static import static

ENCRE = "#1f1f1c"
SURFACE = "#ffffff"
BLEU = "#2a78d6"     # oui
ROUGE = "#c9352b"    # non
NEUTRE = "#f0efec"   # 50 %
GRIS = "#5f5e58"     # texte secondaire (--gris)
POINT = "#9d9c96"    # point au repos dans un nuage (--fleche)
GRILLE = "#e1e0d9"   # filets des axes (--bord)
FONTE = "system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"

LACS = "carte/lacs.geojson"

DEMI_ETENDUE = 18    # échelle de la carte : 50 ± 18 %
CONTOUR = 0.15       # filet entre communes, en px

CONFIG_CARTE = {
    "displayModeBar": "hover",
    "modeBarButtons": [["zoomInMap", "zoomOutMap", "resetViewMap"]],
    "responsive": True,
    "displaylogo": False,
    "scrollZoom": True,
}


CONFIG_NUAGE = {
    "displayModeBar": "hover",
    "modeBarButtons": [["zoom2d", "pan2d", "resetScale2d"]],
    "responsive": True,
    "displaylogo": False,
    # Pas de zoom à la molette : sur un nuage, il vole le défilement de la page.
    "scrollZoom": False,
}


def habiller_carte(figure, emprise, echelle=None):
    """Couleurs, fond sans tuiles et limites de déplacement.

    ``echelle`` : (min, milieu, max) de l'axe de couleur, par défaut le % de oui.
    L'emprise part dans ``layout.meta`` : ``cartes.js`` en tire centre et zoom.
    """
    (x0, y0), (x1, y1) = emprise
    cmin, cmid, cmax = echelle or (50 - DEMI_ETENDUE, 50, 50 + DEMI_ETENDUE)
    largeur, hauteur = x1 - x0, y1 - y0
    figure.update_layout(
        font={"family": FONTE, "color": ENCRE},
        paper_bgcolor=SURFACE,
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        meta={"emprise": [[x0, y0], [x1, y1]]},
        coloraxis={
            "colorscale": [[0, ROUGE], [0.5, NEUTRE], [1, BLEU]],
            "cmin": cmin, "cmid": cmid, "cmax": cmax,
            "showscale": False,
        },
        map={
            "style": {"version": 8, "sources": {}, "layers": [
                {"id": "fond", "type": "background", "paint": {"background-color": SURFACE}},
            ]},
            # Les lacs par-dessus les communes : dans swissBOUNDARIES3D, une
            # commune riveraine s'étend jusqu'au milieu de l'eau.
            "layers": [{"sourcetype": "geojson", "source": static(LACS),
                        "type": "fill", "color": SURFACE}],
            "center": {"lon": (x0 + x1) / 2, "lat": (y0 + y1) / 2},
            "zoom": 6,
            # On ne s'éloigne pas du pays de plus de sa demi-largeur.
            "bounds": {"west": x0 - largeur / 2, "east": x1 + largeur / 2,
                       "south": y0 - hauteur / 2, "north": y1 + hauteur / 2},
        },
    )
    figure.update_traces(marker_opacity=1, marker_line_width=CONTOUR, marker_line_color=SURFACE)
    return figure


def habiller_nuage(figure, titre_x, titre_y):
    """Fond, grille et zéro des deux nuages ACP. Le zéro est plus marqué que la
    grille : sur une ACP, c'est le signe d'une coordonnée qui porte le sens."""
    axe = {
        "showgrid": True, "gridcolor": GRILLE, "gridwidth": 1,
        "zeroline": True, "zerolinecolor": GRIS, "zerolinewidth": 1,
        "showline": False, "ticks": "outside", "tickcolor": GRILLE,
        "title": {"font": {"size": 13}},
    }
    figure.update_layout(
        font={"family": FONTE, "color": ENCRE, "size": 12},
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        margin={"l": 52, "r": 16, "t": 10, "b": 44},
        showlegend=False,
        hovermode="closest",
        xaxis={**axe, "title": {**axe["title"], "text": titre_x}},
        yaxis={**axe, "title": {**axe["title"], "text": titre_y}},
    )
    return figure


def demi_etendue(valeurs):
    """Demi-étendue d'une échelle de couleur centrée sur zéro : le 95ᵉ centile des
    écarts, pour qu'une poignée de valeurs extrêmes n'écrase pas les nuances."""
    ecarts = sorted(abs(v) for v in valeurs)
    return round(ecarts[int(0.95 * (len(ecarts) - 1))], 2) or 1.0
