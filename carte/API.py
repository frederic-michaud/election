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


def _carte(locations, valeurs, survol, echelle=None, attente=(), estimees=None):
    """Une choroplèthe communale, posée sur les communes encore en attente.

    ``attente`` est dessinée en dessous, d'un gris uni : sans elle, le pays
    disparaîtrait tant que rien n'est dépouillé — il ne resterait que les lacs.
    ``estimees`` (locations, valeurs, survol) est une couche à part, que
    ``cartes.js`` peut masquer : le gris réapparaît alors dessous.
    """
    couches = []
    if attente:
        couches.append(_couche(
            list(attente), z=[0] * len(attente), showscale=False,
            colorscale=[[0, charte.ATTENTE], [1, charte.ATTENTE]],
            hovertemplate="<b>%{properties.vogeName}</b><br>pas encore dépouillée<extra></extra>"))
    if estimees and estimees[0]:
        couches.append(_couche(
            estimees[0], z=estimees[1], text=estimees[2], coloraxis="coloraxis",
            hovertemplate="<b>%{properties.vogeName}</b><br>%{text}<extra></extra>"))
    if locations:
        couches.append(_couche(
            locations, z=valeurs, text=survol, coloraxis="coloraxis",
            hovertemplate="<b>%{properties.vogeName}</b><br>%{text}<extra></extra>"))
    figure = charte.habiller_carte(go.Figure(couches), EMPRISE, echelle=echelle)
    if estimees and estimees[0]:
        figure.update_layout(meta={**figure.layout.meta, "estimees": 1 if attente else 0})
    return figure


def _pourcent(oui):
    return f"{oui:.1f} %".replace(".", ",")


def figure_carte(communes):
    """Carte WebGL des résultats par commune, tracée par ``carte/static/carte/cartes.js``.

    ``communes`` : le dict ``sujet["communes"]`` du contrat de vue. Les communes
    estimées par ``run_extrapolation`` ont leur propre couche, au-dessus du gris.
    """
    oui = {ofs: round(r["oui"] * 100, 2) for ofs, r in communes.items() if r["oui"] is not None}
    reelles = [ofs for ofs in oui if communes[ofs]["comptabilise"]]
    estimees = [ofs for ofs in oui if not communes[ofs]["comptabilise"]]
    reelles_set = set(reelles)
    return _carte(reelles,
                  [oui[ofs] for ofs in reelles],
                  [_pourcent(oui[ofs]) for ofs in reelles],
                  attente=[ofs for ofs in communes if ofs not in reelles_set],
                  estimees=(estimees,
                            [oui[ofs] for ofs in estimees],
                            [f"{_pourcent(oui[ofs])} (estimé)" for ofs in estimees]))


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
