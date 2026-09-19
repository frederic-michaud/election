import plotly.graph_objects as go
from django.templatetags.static import static

from scrutin import charte

CONTOURS = "carte/communes.geojson"

# Imprimée par ``manage.py generer_contours`` ; ``tests/test_carte.py`` la vérifie.
# En dur, pour que le serveur n'ouvre jamais les 5,8 Mo de contours.
EMPRISE = ((5.95588, 45.81796), (10.49216, 47.80845))


def _carte(locations, valeurs, survol):
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
    return charte.habiller_carte(figure, EMPRISE)


def figure_carte(communes):
    """Carte WebGL des résultats par commune, tracée par ``carte/static/carte/cartes.js``.

    ``communes`` : le dict ``sujet["communes"]`` du contrat de vue.
    """
    resultats = {ofs: round(r["oui"] * 100, 2) for ofs, r in communes.items()
                 if r["oui"] is not None}
    return _carte(list(resultats),
                  list(resultats.values()),
                  [f"{oui:.1f} %".replace(".", ",") for oui in resultats.values()])
