import plotly.graph_objects as go
from django.templatetags.static import static

from scrutin import charte

CONTOURS = "carte/communes.geojson"

# Emprise du fichier de contours, imprimée par ``manage.py generer_contours``.
# En dur pour que le serveur n'ouvre jamais les 5,8 Mo : ``tests/test_carte.py``
# vérifie qu'elle correspond toujours au fichier.
EMPRISE = ((5.95588, 45.81796), (10.49216, 47.80845))


def _carte(locations, valeurs, survol, echelle=None):
    """Une choroplèthe communale : les contours sont une URL, pas des données.

    plotly.js télécharge ``communes.geojson`` une fois pour toutes les cartes de
    la page, et le navigateur le garde d'une visite à l'autre. Le nom affiché au
    survol vient du fichier lui-même (``%{properties.vogeName}``).
    """
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


def _etendue(valeurs):
    """Demi-étendue de l'échelle de couleur : le 95ᵉ centile des écarts à zéro,
    pour qu'une poignée de communes extrêmes n'écrase pas les nuances du reste."""
    ecarts = sorted(abs(v) for v in valeurs)
    return round(ecarts[int(0.95 * (len(ecarts) - 1))], 2) or 1.0


def _axe(numero, valeurs):
    return {
        "nom": f"Axe {numero}",
        "valeurs": [round(v, 2) for v in valeurs],
        "survol": [f"Axe {numero} : {v:+.2f}".replace(".", ",") for v in valeurs],
        "etendue": _etendue(valeurs),
    }


def figure_carte_acp(profils):
    """Carte des coordonnées ACP par commune, un axe à la fois.

    ``profils`` : le dict de ``pca.donnees.profils_par_commune``. Les axes partent
    tous dans ``layout.meta`` ; ``carte_acp.js`` échange celui qui est affiché.
    """
    communes = sorted(profils)
    axes = [_axe(numero, colonne) for numero, colonne
            in enumerate(zip(*(profils[ofs] for ofs in communes)), start=1)]
    premier = axes[0]
    figure = _carte(communes, premier["valeurs"], premier["survol"],
                    echelle=(-premier["etendue"], 0, premier["etendue"]))
    figure.update_layout(meta={**figure.layout.meta, "axes": axes})
    return figure
