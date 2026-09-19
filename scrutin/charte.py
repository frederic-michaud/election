"""Palette et réglages Plotly, repris de la maquette D′ (couleurs aussi dans style.css)."""

from django.templatetags.static import static

ENCRE = "#1f1f1c"
SURFACE = "#ffffff"
BLEU = "#2a78d6"     # oui
ROUGE = "#c9352b"    # non
NEUTRE = "#f0efec"   # 50 %
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


def habiller_carte(figure, emprise):
    """Couleurs, fond sans tuiles et limites de déplacement.

    L'emprise part dans ``layout.meta`` : ``cartes.js`` en tire centre et zoom.
    """
    (x0, y0), (x1, y1) = emprise
    largeur, hauteur = x1 - x0, y1 - y0
    figure.update_layout(
        font={"family": FONTE, "color": ENCRE},
        paper_bgcolor=SURFACE,
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        meta={"emprise": [[x0, y0], [x1, y1]]},
        coloraxis={
            "colorscale": [[0, ROUGE], [0.5, NEUTRE], [1, BLEU]],
            "cmin": 50 - DEMI_ETENDUE, "cmid": 50, "cmax": 50 + DEMI_ETENDUE,
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
