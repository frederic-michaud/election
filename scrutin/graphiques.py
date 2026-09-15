"""Mise en forme de la page d'accueil, à partir du contrat de vue (aucun ORM)."""

from datetime import date, datetime

import plotly.io as pio

from scrutin import charte

# Demi-largeur de la fourchette, en points : provisoire et identique pour tous
# les objets, faute d'intervalle de confiance dans le contrat (#43).
MARGE_PROVISOIRE = 2.5


def en_json(figure):
    """JSON d'une figure, sûr dans un ``<script>`` (échappé comme ``json_script``)."""
    return (pio.to_json(figure, validate=False)
            .replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026"))


def pourcentage(part):
    """0.4689 → « 46,9 % »."""
    return f"{100 * part:.1f}".replace(".", ",") + " %"


def _css(valeur):
    """Nombre pour un attribut ``style`` : toujours un point décimal."""
    return f"{valeur:.2f}"


def _intervalle(oui_extrapole, marge):
    extrapole = 100 * oui_extrapole
    return max(0.0, extrapole - marge), min(100.0, extrapole + marge)


def barre(oui_connu, oui_extrapole, marge=MARGE_PROVISOIRE):
    """Positions de la barre, en % de sa largeur. Le dépouillé n'est dessiné que hors de l'intervalle."""
    connu, extrapole = 100 * oui_connu, 100 * oui_extrapole
    bas, haut = _intervalle(oui_extrapole, marge)
    forme = {"bas": _css(bas), "largeur": _css(haut - bas), "depouille": None}
    if not bas <= connu <= haut:
        monte = extrapole >= connu
        cible = bas if monte else haut
        forme["depouille"] = {
            "position": _css(connu),
            "trajet_debut": _css(min(connu, cible)),
            "trajet_largeur": _css(abs(cible - connu)),
            "fleche": _css(cible),
            "sens": "droite" if monte else "gauche",
        }
    return forme


def panneau(sujet, marge=MARGE_PROVISOIRE):
    if sujet["oui_extrapole"] is None:
        return {"nom": sujet["nom"], "attente": True}
    bas, haut = _intervalle(sujet["oui_extrapole"], marge)
    bornes = (f"{bas:.1f} – {haut:.1f} %").replace(".", ",")
    return {
        "nom": sujet["nom"],
        "verdict": "oui" if sujet["oui_extrapole"] >= 0.5 else "non",
        "extrapole": pourcentage(sujet["oui_extrapole"]),
        "connu": pourcentage(sujet["oui_connu"]),
        "bornes": bornes,
        "barre": barre(sujet["oui_connu"], sujet["oui_extrapole"], marge),
        "description": (f"Extrapolé {pourcentage(sujet['oui_extrapole'])}, fourchette {bornes} ; "
                        f"dépouillé {pourcentage(sujet['oui_connu'])}"),
    }


def accueil(vue):
    """Contexte de ``home.html``, sans les cartes."""
    mise_a_jour = vue["mise_a_jour"]
    return {
        "date": date.fromisoformat(vue["date"]),
        "mise_a_jour": datetime.fromisoformat(mise_a_jour) if mise_a_jour else None,
        "avance": pourcentage(vue["avance"]),
        "commence": vue["avance"] > 0,
        "jauge": _css(100 * vue["avance"]),
        "panneaux": [panneau(sujet) for sujet in vue["sujets"]],
        "config_carte": charte.CONFIG_CARTE,
    }
