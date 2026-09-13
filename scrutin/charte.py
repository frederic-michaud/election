"""Charte graphique : la palette et les réglages Plotly, en un seul endroit.

Transcription de `maquette/charte.js` tel que l'utilise la variante **D′**,
validée le 2026-09-13 (`PLAN_MODERNISATION.md` Partie 7). Les mêmes valeurs
vivent en variables CSS dans `scrutin/static/scrutin/style.css` : ce qui est
ici sert aux figures, ce qui est là-bas sert à la page, et les deux doivent
dire la même chose.

Aucune figure ne fixe ses couleurs elle-même — elles passent toutes par
`appliquer_charte`.
"""

# ── La palette ───────────────────────────────────────────────────────────
# Validée sur fond clair (Partie 7). Le rouge du « non » n'est pas encore
# passé par `validate_palette.js` : c'est une tâche 7.3.
FOND = "#fcfcfb"        # la page
PANNEAU = "#ffffff"     # les cartes-panneaux, et donc le fond des figures
BORD = "#e1e0d9"
ENCRE_1 = "#1f1f1c"     # texte principal
ENCRE_2 = "#5f5e58"     # texte secondaire, axes
OUI = "#2a78d6"
OUI_CLAIR = "#86b6ef"   # même teinte, plus clair = estimé
NON = "#c9352b"
NEUTRE = "#f0efec"      # milieu de l'échelle divergente, ancré à 50 %

FONTE = "system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"

# ── La carte ─────────────────────────────────────────────────────────────
# Bornes symétriques autour de 50 : 32 % … 68 %. Au-delà, on ne distingue
# plus rien entre deux communes également acquises.
DEMI_ETENDUE = 18
CONTOUR = 0.15          # filet entre communes, dans la couleur du panneau
OPACITE = 1

#: « penche non » ← neutre → « penche oui », lisible aussi en vision daltonienne.
ECHELLE_DIVERGENTE = [(0.0, NON), (0.5, NEUTRE), (1.0, OUI)]

#: Pas de barre d'outils Plotly : le site n'est pas un outil d'analyse.
CONFIG_PLOTLY = {"displayModeBar": False, "responsive": True, "displaylogo": False}


def appliquer_charte(figure):
    """Fonte, couleurs de fond et marges communes à toutes les figures."""
    figure.update_layout(
        font={"family": FONTE, "color": ENCRE_1, "size": 14},
        paper_bgcolor=PANNEAU,
        plot_bgcolor=PANNEAU,
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
    )
    return figure
