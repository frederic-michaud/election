"""Mise en forme de la page des anomalies, à partir du contrat de vue (aucun ORM)."""

from datetime import date, datetime

import plotly.graph_objects as go
from django.utils.html import conditional_escape, format_html
from django.utils.safestring import mark_safe

from pca.figures import _etiquette as etiquette
from scrutin import charte
from scrutin.graphiques import en_json, pourcentage

# Infobulle du σ dans le résumé d'une commune.
SIGMA = format_html('<abbr title="{}">σ</abbr>',
                    "Écart-type : l'écart ordinaire entre le résultat d'une commune et sa "
                    "prédiction. Au-delà de 3 σ, le hasard n'explique presque plus l'écart.")


def _nombre(valeur, chiffres=1):
    return f"{valeur:.{chiffres}f}".replace(".", ",").replace("-", "−")


def _part(objet):
    return objet["oui"] / (objet["oui"] + objet["non"])


def corriger(objets, correction):
    """Les objets tels que la correction les rétablit."""
    corriges = [dict(o) for o in objets]
    if correction is None:
        return corriges
    i = correction["objets"][0]
    if correction["type"] == "inversion":
        corriges[i]["oui"], corriges[i]["non"] = objets[i]["non"], objets[i]["oui"]
    elif correction["type"] == "echange":
        k = correction["objets"][1]
        for champ in ("oui", "non", "bulletins"):
            corriges[i][champ], corriges[k][champ] = objets[k][champ], objets[i][champ]
    else:
        corriges[i][correction["champ"]] = correction["corrige"]
        corriges[i]["bulletins"] += correction["corrige"] - correction["saisi"]
    return corriges


def correction_en_clair(correction, noms):
    objets = [f"« {noms[i]} »" for i in correction["objets"]]
    if correction["type"] == "inversion":
        return f"oui et non inversés sur {objets[0]}"
    if correction["type"] == "echange":
        return f"résultats de {objets[0]} et {objets[1]} intervertis"
    return f"{objets[0]} : {correction['saisi']} {correction['champ']} saisis pour {correction['corrige']}"


def _ecart_de_vote(commune, noms):
    ecarts = [o["z"] for o in commune["objets"]]
    i = max(range(len(ecarts)), key=lambda k: abs(ecarts[k]))
    return format_html("écart de {} {} sur « {} »", _nombre(ecarts[i]), SIGMA, noms[i])


def _ecart_de_bulletins(commune):
    bulletins = [o["bulletins"] for o in commune["objets"]]
    ecart = (max(bulletins) - min(bulletins)) / max(bulletins)
    return (f"bulletins de {min(bulletins)} à {max(bulletins)} selon l'objet : "
            f"{pourcentage(ecart)} d'écart, d'habitude {pourcentage(commune['bulletins_habituel'] or 0)}")


def resume(commune, noms):
    """Une ligne de HTML : la faute probable, sinon ce qui cloche."""
    motifs = commune["motifs"]
    morceaux = []
    if "correction" in motifs:
        morceaux.append(correction_en_clair(commune["correction"], noms))
    elif "vote" in motifs or "bulletins" not in motifs:
        morceaux.append(_ecart_de_vote(commune, noms))
    if "bulletins" in motifs:
        morceaux.append(_ecart_de_bulletins(commune))
    return mark_safe(" ; ".join(conditional_escape(m) for m in morceaux))


def figure_nuage(communes, i):
    """Observé contre prédit, toutes les communes, pour l'objet ``i`` ;
    ``anomalies.js`` y pose la commune ouverte."""
    x = [round(100 * c["objets"][i]["predit"], 2) for c in communes]
    y = [round(100 * _part(c["objets"][i]), 2) for c in communes]
    figure = go.Figure([
        go.Scatter(x=[0, 100], y=[0, 100], mode="lines", hoverinfo="skip",
                   line={"color": charte.GRILLE, "width": 1}),
        go.Scattergl(x=x, y=y, mode="markers", hovertext=[c["nom"] for c in communes],
                     marker={"size": 4, "color": charte.POINT, "opacity": 0.5},
                     hovertemplate="%{hovertext}<br>prédit %{x:.1f} %, observé %{y:.1f} %<extra></extra>"),
    ])
    charte.habiller_nuage(figure, "prédit, % de oui", "observé")
    # Même échelle sur les deux axes, cadrée sur le nuage : la diagonale reste à 45°.
    bas, haut = max(0, min(x + y) - 4), min(100, max(x + y) + 4)
    figure.update_layout(xaxis={"range": [bas, haut]}, yaxis={"range": [bas, haut]},
                         margin={"l": 44, "r": 8, "t": 8, "b": 40})
    return figure


def _lignes(figure, etiquettes):
    """Une ligne par objet, son étiquette écrite au-dessus : dans une colonne
    étroite, des étiquettes sur l'axe prendraient la moitié de la largeur."""
    for i, etiquette_ligne in enumerate(etiquettes):
        figure.add_annotation(xref="paper", x=0, xanchor="left", y=i - 0.5, yanchor="top",
                              text=etiquette_ligne, showarrow=False, align="left",
                              font={"size": 12, "color": charte.ENCRE})
    figure.update_layout(yaxis={"range": [len(etiquettes) - 0.5, -0.5], "zeroline": False,
                                "showgrid": False, "showticklabels": False, "ticks": "",
                                "tickvals": list(range(len(etiquettes)))})


def figure_bulletins(objets, noms):
    """Oui, non et blancs de chaque objet : une commune vote une seule fois,
    les barres doivent être presque égales. Un trait vertical au total de
    chaque objet : l'espace entre deux traits est l'écart de bulletins."""
    rangs = list(range(len(objets)))
    blancs = [o["bulletins"] - o["oui"] - o["non"] for o in objets]
    totaux = [o["bulletins"] for o in objets]
    # La barre occupe le bas de sa ligne, sous l'étiquette.
    barre = {"y": rangs, "orientation": "h", "width": 0.38, "offset": 0}
    figure = go.Figure([
        go.Bar(x=[o["oui"] for o in objets], name="oui", marker_color=charte.BLEU, **barre),
        go.Bar(x=[o["non"] for o in objets], name="non", marker_color=charte.ROUGE, **barre),
        go.Bar(x=blancs, name="blancs et nuls", marker_color=charte.ENCRE, **barre),
    ])
    charte.habiller_nuage(figure, "bulletins", "")
    for total in totaux:
        figure.add_shape(type="line", x0=total, x1=total, yref="paper", y0=0, y1=1,
                         line={"color": charte.ENCRE, "width": 1, "dash": "dot"})
    if len(objets) > 1:
        figure.add_annotation(x=(min(totaux) + max(totaux)) / 2, yref="paper", y=1, yanchor="bottom",
                              text=f"écart : {max(totaux) - min(totaux)}", showarrow=False,
                              font={"size": 11, "color": charte.GRIS})
    # Les blancs sont trop minces pour se lire sur la barre : leur nombre est écrit.
    _lignes(figure, [f"{nom}<br><span style='font-size:11px;color:{charte.GRIS}'>{total} bulletins, "
                     f"{blanc} {'blanc ou nul' if blanc == 1 else 'blancs ou nuls'}</span>"
                     for nom, total, blanc in zip(noms, totaux, blancs)])
    figure.update_layout(barmode="stack", showlegend=False,
                         margin={"l": 8, "r": 16, "t": 22, "b": 40})
    return figure


def figure_historique(historique, objets, jour, noms):
    """L'écart de la commune à chaque objet passé : une commune coutumière des
    écarts n'est pas une commune qui s'est trompée."""
    figure = go.Figure([
        go.Scatter(x=[h["date"] for h in historique], y=[h["z"] for h in historique],
                   mode="markers", hovertext=[etiquette(h["nom"]) for h in historique],
                   marker={"size": 6, "color": charte.POINT},
                   hovertemplate="%{hovertext}<br>%{y:.1f} σ<extra></extra>"),
        go.Scatter(x=[jour] * len(objets), y=[o["z"] for o in objets], mode="markers",
                   hovertext=noms, marker={"size": 9, "color": charte.ROUGE},
                   hovertemplate="%{hovertext}<br>%{y:.1f} σ<extra></extra>"),
    ])
    charte.habiller_nuage(figure, "", "écart au modèle (σ)")
    figure.add_hrect(y0=-3, y1=3, fillcolor=charte.NEUTRE, line_width=0, layer="below")
    figure.update_layout(margin={"l": 52, "r": 8, "t": 8, "b": 30})
    return figure


def figure_semblables(commune, corriges, par_ofs, noms):
    """Le % de oui des communes semblables, une ligne par objet : la commune en
    rouge et, si la correction la déplace, le cercle où elle la ramène."""
    semblables = [par_ofs[v] for v in commune["voisines"] if v in par_ofs]
    # Étalement vertical fixe, pour que deux communes au même % restent lisibles.
    etalement = [0.5 * ((0.618 * k) % 1 - 0.5) for k in range(len(semblables))]
    rangs = list(range(len(noms)))
    traces = [go.Scatter(
        x=[100 * _part(c["objets"][i]) for i in rangs for c in semblables],
        y=[i + 0.2 + 0.6 * e for i in rangs for e in etalement],
        hovertext=[f"{c['nom']} {c['canton']}" for _ in rangs for c in semblables],
        mode="markers", marker={"size": 7, "color": charte.POINT, "opacity": 0.8},
        hovertemplate="%{hovertext}<br>%{x:.1f} % de oui<extra></extra>")]
    deplaces = [i for i in rangs
                if (corriges[i]["oui"], corriges[i]["non"]) != (commune["objets"][i]["oui"], commune["objets"][i]["non"])]
    for i in deplaces:
        traces.append(go.Scatter(x=[100 * _part(commune["objets"][i]), 100 * _part(corriges[i])], y=[i + 0.2, i + 0.2],
                                 mode="lines", hoverinfo="skip",
                                 line={"color": charte.ENCRE, "width": 1, "dash": "dot"}))
    traces.append(go.Scatter(
        x=[100 * _part(o) for o in commune["objets"]], y=[i + 0.2 for i in rangs], mode="markers",
        marker={"size": 10, "color": charte.ROUGE, "line": {"width": 1.5, "color": charte.SURFACE}},
        hovertemplate=f"{commune['nom']}<br>%{{x:.1f}} % de oui<extra></extra>"))
    traces.append(go.Scatter(
        x=[100 * _part(corriges[i]) for i in deplaces], y=[i + 0.2 for i in deplaces], mode="markers",
        marker={"size": 11, "symbol": "circle-open", "color": charte.ENCRE, "line": {"width": 2}},
        hovertemplate="corrigée<br>%{x:.1f} % de oui<extra></extra>"))
    figure = go.Figure(traces)
    charte.habiller_nuage(figure, "% de oui", "")
    _lignes(figure, noms)
    figure.update_layout(xaxis={"zeroline": False}, margin={"l": 8, "r": 12, "t": 8, "b": 40})
    return figure


def fiche(commune, par_ofs, noms, jour):
    objets = commune["objets"]
    # La correction n'est montrée que si elle explique quelque chose.
    corriges = corriger(objets, commune["correction"] if "correction" in commune["motifs"] else None)
    return {
        "ofs": commune["ofs"],
        "nom": commune["nom"],
        "canton": commune["canton"],
        "niveau": commune["niveau"],
        "resume": resume(commune, noms),
        "chi2": _nombre(commune["chi2"]),
        "chi2_corrige": (_nombre(commune["chi2_corrige"]) if "correction" in commune["motifs"]
                         else None),
        "depuis": datetime.fromisoformat(commune["signalee_depuis"]) if commune["signalee_depuis"] else None,
        "note": commune["note"],
        # Ce que anomalies.js pose sur les nuages : la commune, et où la correction la ramène.
        "points": [{
            "x": round(100 * o["predit"], 2),
            "y": round(100 * _part(o), 2),
            "corrige": round(100 * _part(c), 2) if (c["oui"], c["non"]) != (o["oui"], o["non"]) else None,
        } for o, c in zip(objets, corriges)],
        "bulletins": en_json(figure_bulletins(objets, noms)),
        "semblables": (en_json(figure_semblables(commune, corriges, par_ofs, noms))
                       if commune["voisines"] else None),
        "historique": en_json(figure_historique(commune["historique"] or [], objets, jour, noms)),
    }


def page_anomalies(vue):
    """Contexte de ``anomalies.html``."""
    noms = [etiquette(o["nom"]) for o in vue["objets"]]
    communes = vue["communes"]
    par_ofs = {c["ofs"]: c for c in communes}
    signalees = [c for c in communes if c["niveau"] != "vert"]
    return {
        "date": date.fromisoformat(vue["date"]),
        "mise_a_jour": datetime.fromisoformat(vue["mise_a_jour"]) if vue["mise_a_jour"] else None,
        "pret": bool(communes),
        "depouillees": vue["depouillees"],
        "seuil": vue["seuil"],
        "nb_communes": len(communes),
        "nb_rouges": sum(c["niveau"] == "rouge" for c in communes),
        "nb_oranges": sum(c["niveau"] == "orange" for c in communes),
        "objets": noms,
        "signalees": [fiche(c, par_ofs, noms, vue["date"]) for c in signalees],
        "nuages": [en_json(figure_nuage(communes, i)) for i in range(len(noms))] if communes else [],
        "config": charte.CONFIG_NUAGE,
    }
