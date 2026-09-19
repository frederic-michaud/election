import plotly.graph_objects as go
from django.templatetags.static import static

from scrutin import charte

CONTOURS = "carte/communes.geojson"

# Imprimée par ``manage.py generer_contours`` ; ``tests/test_carte.py`` la vérifie.
# En dur, pour que le serveur n'ouvre jamais les 5,8 Mo de contours.
EMPRISE = ((5.95588, 45.81796), (10.49216, 47.80845))


def _carte(locations, valeurs, survol, echelle=None):
    """Une choroplèthe communale. Les contours sont une URL : plotly.js les
    télécharge une fois pour toutes les cartes de la page."""
    figure = go.Figure(go.Choroplethmap(
        geojson=static(CONTOURS),
        featureidkey="properties.vogeId",
        locations=locations,
        z=valeurs,
        text=survol,
        hovertemplate="<b>%{properties.vogeName}</b><br>%{text}<extra></extra>",
        coloraxis="coloraxis"))
    return charte.habiller_carte(figure, EMPRISE, echelle=echelle)


def figure_carte(communes):
    """Carte WebGL des résultats par commune, tracée par ``carte/static/carte/cartes.js``.

    ``communes`` : le dict ``sujet["communes"]`` du contrat de vue.
    """
    resultats = {ofs: round(r["oui"] * 100, 2) for ofs, r in communes.items()
                 if r["oui"] is not None}
    return _carte(list(resultats),
                  list(resultats.values()),
                  [f"{oui:.1f} %".replace(".", ",") for oui in resultats.values()])


def _axe(numero, valeurs):
    return {
        "nom": f"Axe {numero}",
        "valeurs": [round(v, 2) for v in valeurs],
        "survol": [f"Axe {numero} : {v:+.2f}".replace(".", ",") for v in valeurs],
        "etendue": charte.demi_etendue(valeurs),
    }


def figure_carte_acp(profils):
    """Coordonnées ACP par commune. Les six axes sont dans ``layout.meta`` :
    ``carte_acp.js`` choisit celui qu'il affiche."""
    communes = sorted(profils)
    axes = [_axe(numero, colonne) for numero, colonne
            in enumerate(zip(*(profils[ofs] for ofs in communes)), start=1)]
    premier = axes[0]
    figure = _carte(communes, premier["valeurs"], premier["survol"],
                    echelle=(-premier["etendue"], 0, premier["etendue"]))
    figure.update_layout(meta={**figure.layout.meta, "axes": axes})
    return figure
