"""Mise en forme de la page des anomalies, à partir du contrat de vue (aucun ORM)."""

from datetime import date, datetime

import plotly.graph_objects as go

from carte.API import figure_carte_voisines
from pca.figures import _etiquette as etiquette
from scrutin import charte
from scrutin.graphiques import en_json, pourcentage

NB_AUTRES = 30       # communes vertes listées, les plus éloignées du modèle
MARGE_CARTE = 0.015  # degrés autour des voisines


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
    return f"écart de {_nombre(ecarts[i])} σ sur « {noms[i]} »"


def _ecart_de_bulletins(commune):
    bulletins = [o["bulletins"] for o in commune["objets"]]
    ecart = (max(bulletins) - min(bulletins)) / max(bulletins)
    return (f"bulletins de {min(bulletins)} à {max(bulletins)} selon l'objet : "
            f"{pourcentage(ecart)} d'écart, d'habitude {pourcentage(commune['bulletins_habituel'] or 0)}")


def resume(commune, noms):
    """Une ligne : la faute probable, sinon ce qui cloche."""
    motifs = commune["motifs"]
    morceaux = []
    if "correction" in motifs:
        morceaux.append(correction_en_clair(commune["correction"], noms))
    elif "vote" in motifs or "bulletins" not in motifs:
        morceaux.append(_ecart_de_vote(commune, noms))
    if "bulletins" in motifs:
        morceaux.append(_ecart_de_bulletins(commune))
    return " ; ".join(morceaux)


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


def figure_bulletins(objets, noms):
    """Oui, non et blancs de chaque objet : une commune vote une seule fois,
    les barres doivent être presque égales."""
    noms = [f"{n} " for n in noms]
    figure = go.Figure([
        go.Bar(y=noms, x=[o["oui"] for o in objets], name="oui", marker_color=charte.BLEU, orientation="h"),
        go.Bar(y=noms, x=[o["non"] for o in objets], name="non", marker_color=charte.ROUGE, orientation="h"),
        go.Bar(y=noms, x=[o["bulletins"] - o["oui"] - o["non"] for o in objets], name="blancs et nuls",
               marker_color=charte.GRILLE, orientation="h",
               text=[o["bulletins"] for o in objets], textposition="outside", cliponaxis=False),
    ])
    charte.habiller_nuage(figure, "bulletins", "")
    figure.update_layout(barmode="stack", showlegend=False, hovermode="y unified",
                         yaxis={"autorange": "reversed", "zeroline": False, "showgrid": False},
                         margin={"l": 8, "r": 44, "t": 8, "b": 40})
    figure.update_yaxes(automargin=True)
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


def figure_voisines(commune, par_ofs, noms):
    """Les voisines colorées par leur écart sur l'objet où la commune s'écarte le plus."""
    ecarts = [abs(o["z"]) for o in commune["objets"]]
    i = ecarts.index(max(ecarts))
    autour = [commune] + [par_ofs[v] for v in commune["voisines"] if v in par_ofs]
    valeurs = {c["ofs"]: c["objets"][i]["z"] for c in autour}
    survol = {c["ofs"]: f"{_nombre(c['objets'][i]['z'])} σ sur « {noms[i]} »" for c in autour}
    centres = [c["centre"] for c in autour if c["centre"]]
    emprise = ((min(x for x, _ in centres) - MARGE_CARTE, min(y for _, y in centres) - MARGE_CARTE),
               (max(x for x, _ in centres) + MARGE_CARTE, max(y for _, y in centres) + MARGE_CARTE))
    return figure_carte_voisines(commune["ofs"], valeurs, survol, emprise)


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
        "objets": [{
            "nom": nom,
            "observe": pourcentage(_part(o)),
            "predit": pourcentage(o["predit"]),
            "z": _nombre(o["z"]),
            "z_voisines": None if o["z_voisines"] is None else _nombre(o["z_voisines"]),
        } for nom, o in zip(noms, objets)],
        # Ce que anomalies.js pose sur les nuages : la commune, et où la correction la ramène.
        "points": [{
            "x": round(100 * o["predit"], 2),
            "y": round(100 * _part(o), 2),
            "corrige": round(100 * _part(c), 2) if (c["oui"], c["non"]) != (o["oui"], o["non"]) else None,
        } for o, c in zip(objets, corriges)],
        "bulletins": en_json(figure_bulletins(objets, noms)),
        "carte": en_json(figure_voisines(commune, par_ofs, noms)) if commune["centre"] else None,
        "historique": en_json(figure_historique(commune["historique"] or [], objets, jour, noms)),
    }


def page_anomalies(vue):
    """Contexte de ``anomalies.html``."""
    noms = [etiquette(o["nom"]) for o in vue["objets"]]
    communes = vue["communes"]
    par_ofs = {c["ofs"]: c for c in communes}
    signalees = [c for c in communes if c["niveau"] != "vert"]
    vertes = [c for c in communes if c["niveau"] == "vert"]
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
        "autres": [{"nom": c["nom"], "canton": c["canton"], "resume": resume(c, noms),
                    "chi2": _nombre(c["chi2"])} for c in vertes[:NB_AUTRES]],
        "nb_vertes": len(vertes),
        "nuages": [en_json(figure_nuage(communes, i)) for i in range(len(noms))] if communes else [],
        "config": charte.CONFIG_NUAGE,
        "config_carte": charte.CONFIG_CARTE,
    }
