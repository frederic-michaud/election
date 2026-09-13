"""Ce que la page d'accueil affiche : figures Plotly et valeurs formatées.

Ces fonctions ne consomment que le contrat de vue construit par
`scrutin.donnees` : aucun accès à l'ORM ici. Elles ne rendent pas non plus de
HTML de mise en page — ça, c'est l'affaire des gabarits ; elles préparent les
valeurs que les gabarits n'ont pas le droit de calculer eux-mêmes.

Les nombres destinés à du CSS (`left:…%`) sortent d'ici **en chaînes à point
décimal**. Rendus comme des flottants, la localisation de Django les écrirait
« 46,9 » le jour où le site passera en français, et la règle serait ignorée.
"""

import json

import plotly
import plotly.express as px
import plotly.io

from scrutin.charte import (
    CONFIG_PLOTLY,
    ENCRE_2,
    OUI,
    OUI_CLAIR,
    appliquer_charte,
)

#: Demi-largeur de la fourchette affichée, en points de pourcentage.
#:
#: **Provisoire et sans aucune valeur statistique** : c'est un gabarit
#: d'affichage, pas une mesure. Le contrat de vue ne porte pas encore
#: `ic_bas` / `ic_haut` — l'intervalle par bootstrap est une tâche D1 de la
#: voie Moteur, et il ne servait à rien de retenir tout le passage du design
#: en l'attendant (décision du 2026-09-13, `PLAN_MODERNISATION.md` D1).
#:
#: Le jour où la voie Moteur calcule l'intervalle : cette constante disparaît,
#: `ic_bas` / `ic_haut` entrent au contrat et dans `tests/test_contrat.py`, et
#: l'on tranche ce que la page en dit au public.
MARGE_FOURCHETTE = 2.5

MOIS = ("janvier", "février", "mars", "avril", "mai", "juin",
        "juillet", "août", "septembre", "octobre", "novembre", "décembre")


def en_div(figure):
    """La figure en `<div>` prêt pour un gabarit, sans recharger plotly.js."""
    return plotly.offline.plot(figure, include_plotlyjs=False, output_type="div",
                               config=CONFIG_PLOTLY)


def figure_json(figure):
    r"""La figure en JSON, à déposer dans la page pour que le navigateur la trace.

    Plutôt que le `<div>` tout fait de `plotly.offline` : son enrobage fixe des
    hauteurs en pourcentage, qui ne résolvent rien contre un conteneur dont la
    hauteur vient d'un `aspect-ratio` — la carte débordait alors du panneau, par
    dessus le reste de la page. La maquette traçait déjà dans le conteneur
    lui-même ; c'est ce qu'on reprend.

    `</` est échappé : la chaîne finit dans un `<script>`, et un `</script>` au
    milieu d'un nom de commune y fermerait la balise. `<\/` est un échappement
    JSON valide.
    """
    return plotly.io.to_json(figure).replace("</", "<\\/")


def pourcent(part, decimales=1):
    """0.469 → « 46,9 % », virgule décimale et espace insécable."""
    return f"{100 * part:.{decimales}f}".replace(".", ",") + " %"


def date_longue(iso):
    """« 2026-09-27 » → « 27 septembre 2026 »."""
    annee, mois, jour = (int(part) for part in iso.split("-"))
    return f"{jour} {MOIS[mois - 1]} {annee}"


def _css(valeur):
    """Un pourcentage de position, en chaîne à point décimal."""
    return f"{valeur:.3f}"


def _barre(oui_connu, oui_extrapole, marge):
    """La géométrie de la barre finale, en pourcentages de sa largeur.

    Le rail teinté dit la majorité, la moustache l'intervalle, et le trait
    gris le dépouillé — ce dernier **seulement s'il tombe hors de
    l'intervalle** : dedans, la flèche ne ferait que du bruit.
    """
    connu, extrapole = 100 * oui_connu, 100 * oui_extrapole
    bas, haut = max(0.0, extrapole - marge), min(100.0, extrapole + marge)
    cible = bas if extrapole >= connu else haut
    return {
        "moustache_gauche": _css(bas),
        "moustache_largeur": _css(haut - bas),
        "montrer_connu": not bas <= connu <= haut,
        "connu": _css(connu),
        "trajet_gauche": _css(min(connu, cible)),
        "trajet_largeur": _css(abs(cible - connu)),
        "cible": _css(cible),
        "sens": "droite" if extrapole >= connu else "gauche",
    }


def accueil(vue):
    """Tout ce que `home.html` affiche, prêt à rendre.

    C'est le seul point d'entrée de la vue d'accueil : `views.py` ne fait que
    passer le contrat ici, et ne calcule rien.
    """
    return {
        "date": date_longue(vue["date"]),
        "avance": pourcent(vue["avance"]),
        "avance_css": _css(100 * vue["avance"]),
        "panneaux": panneaux(vue),
        "config_plotly": json.dumps(CONFIG_PLOTLY),
    }


def panneaux(vue):
    """Un panneau par objet de votation : les valeurs, la barre, la carte.

    Le verdict n'est porté que par la couleur (`oui` / `non`), comme l'a
    tranché la maquette ; l'`aria-label` de la barre porte les mêmes chiffres
    en toutes lettres, pour qui ne voit pas la couleur.
    """
    from carte.figure import carte  # ici : `carte` importe la charte, pas l'inverse

    marge = MARGE_FOURCHETTE
    liste = []
    for sujet in vue["sujets"]:
        extrapole = 100 * sujet["oui_extrapole"]
        verdict = "oui" if sujet["oui_extrapole"] >= 0.5 else "non"
        bas, haut = max(0.0, extrapole - marge), min(100.0, extrapole + marge)
        liste.append({
            "nom": sujet["nom"],
            "verdict": verdict,
            "extrapole": pourcent(sujet["oui_extrapole"]),
            "connu": pourcent(sujet["oui_connu"]),
            # Les bornes ne se coupent jamais entre elles : espaces insécables.
            "bornes": f"{bas:.1f}".replace(".", ",") + " – "
                      + f"{haut:.1f}".replace(".", ",") + " %",
            "barre": _barre(sujet["oui_connu"], sujet["oui_extrapole"], marge),
            "resume": (f"Extrapolé {pourcent(sujet['oui_extrapole'])}, "
                       f"fourchette de {pourcent(bas / 100)} à {pourcent(haut / 100)} ; "
                       f"dépouillé {pourcent(sujet['oui_connu'])}"),
            "carte": figure_json(carte(sujet["communes"])),
        })
    return liste


def clean_name(name):
        if len(name.split('(')) > 1:
            return name.split('(')[1].split(')')[0]
        return "AVS-TVA"


def histogramme(vue):
    """L'histogramme dépouillé / extrapolé.

    Plus affiché sur l'accueil depuis la variante D′ — les panneaux disent la
    même chose en plus lisible — mais toujours construit ici : c'est cette
    fonction que la branche `maquette` appelle pour fabriquer ses figures.
    """
    noms = [clean_name(sujet["nom"]) for sujet in vue["sujets"]]
    connus = [sujet["oui_connu"] for sujet in vue["sujets"]]
    extrapoles = [sujet["oui_extrapole"] for sujet in vue["sujets"]]
    ddf = {
        "sujet": noms + noms,
        "pourcentage de oui": ["Déja dépouillés"] * len(connus) + ["Extrapolés"] * len(extrapoles),
        "value": connus + extrapoles,
    }
    ddf["formated_value"] = [f"{100*v:.1f}%" for v in ddf["value"]]
    figure = px.bar(ddf, x="sujet", y="value", color="pourcentage de oui",
                    barmode="group", title="", hover_name="sujet",
                    text="formated_value",
                    # Même teinte, plus clair = estimé.
                    color_discrete_sequence=[OUI, OUI_CLAIR])
    figure.update_layout(
        margin={"l": 48, "r": 8, "t": 16, "b": 40},
        legend={"orientation": "h", "y": -0.18, "title": {"text": ""}},
        xaxis={"title": {"text": ""}, "showgrid": False},
        yaxis={"title": {"text": ""}, "tickformat": ".0%", "zeroline": False, "range": [0, 1]},
    )
    # L'information n°1 d'une votation : le seuil qu'il faut franchir.
    figure.add_hline(y=0.5, line={"color": ENCRE_2, "width": 1, "dash": "dot"},
                     annotation={"text": "majorité", "font": {"size": 12, "color": ENCRE_2}})
    return en_div(appliquer_charte(figure))
