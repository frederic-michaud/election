import plotly.graph_objects as go
from django.templatetags.static import static

from scrutin import charte

CONTOURS = "carte/communes.geojson"

# Imprimée par ``manage.py generer_contours`` ; ``tests/test_carte.py`` la vérifie.
# En dur, pour que le serveur n'ouvre jamais les 5,8 Mo de contours.
EMPRISE = ((5.95588, 45.81796), (10.49216, 47.80845))


def _couche(locations, **traits):
    """Une couche de communes. Les contours sont une URL : plotly.js les
    télécharge une fois pour toutes les cartes de la page."""
    return go.Choroplethmap(geojson=static(CONTOURS), featureidkey="properties.vogeId",
                            locations=locations, showlegend=False, **traits)


def _carte(locations, valeurs, survol, echelle=None, attente=(), emprise=EMPRISE):
    """Une choroplèthe communale, posée sur les communes encore en attente.

    ``attente`` est dessinée en dessous, d'un gris uni : sans elle, le pays
    disparaîtrait tant que rien n'est dépouillé — il ne resterait que les lacs.
    """
    couches = []
    if attente:
        couches.append(_couche(
            list(attente), z=[0] * len(attente), showscale=False,
            colorscale=[[0, charte.ATTENTE], [1, charte.ATTENTE]],
            hovertemplate="<b>%{properties.vogeName}</b><br>pas encore dépouillée<extra></extra>"))
    couches.append(_couche(
        locations, z=valeurs, text=survol, coloraxis="coloraxis",
        hovertemplate="<b>%{properties.vogeName}</b><br>%{text}<extra></extra>"))
    return charte.habiller_carte(go.Figure(couches), emprise, echelle=echelle)


def figure_carte(communes):
    """Carte WebGL des résultats par commune, tracée par ``carte/static/carte/cartes.js``.

    ``communes`` : le dict ``sujet["communes"]`` du contrat de vue.
    """
    resultats = {ofs: round(r["oui"] * 100, 2) for ofs, r in communes.items()
                 if r["oui"] is not None}
    return _carte(list(resultats),
                  list(resultats.values()),
                  [f"{oui:.1f} %".replace(".", ",") for oui in resultats.values()],
                  attente=[ofs for ofs in communes if ofs not in resultats])


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


def figure_carte_voisines(ofs, ecarts, survol, emprise):
    """Une commune et ses voisines, colorées par leur écart au modèle (en σ).

    ``ecarts`` et ``survol`` : {numéro OFS: valeur}, la commune comprise ; elle
    est cernée d'un trait plus épais.
    """
    figure = _carte(list(ecarts), list(ecarts.values()), list(survol.values()),
                    echelle=(-5, 0, 5), emprise=emprise)
    figure.add_trace(_couche([ofs], z=[0], showscale=False, hoverinfo="skip",
                             colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
                             marker={"line": {"width": 2.5, "color": charte.ENCRE}}))
    return figure
