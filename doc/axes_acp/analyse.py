"""Que mesurent les axes de l'ACP ? Les calculs du document doc/axes_acp.pdf.

Lit la base réelle en lecture seule et les sources mises en cache dans
``var/sources/``, puis écrit ``resultats.json`` et les figures de ``figures/``.
Aucun ORM : le script lit SQLite directement et tourne donc sans Django.

    pip install matplotlib typst          # en plus de requirements/calcul.txt
    python doc/axes_acp/analyse.py --base var/reel-veille.sqlite3
    python doc/axes_acp/construire.py     # → doc/axes_acp.pdf

Sources (URL de rafraîchissement) :
- Swissvotes (Année politique suisse, Université de Berne), jeu de données et codebook :
  https://swissvotes.ch/page/dataset/swissvotes_dataset.csv
  https://swissvotes.ch/page/dataset/codebook-de.pdf
- OFS, force des partis au Conseil national par commune, cube STAT-TAB
  px-x-1702020000_105 (même API PX-Web que ``importer_historique``) :
  ``python doc/axes_acp/analyse.py --telecharger`` le met en cache.
- Contours : ``carte/static/carte/communes.geojson`` et ``lacs.geojson``.
"""

import argparse
import json
import sqlite3
import urllib.request
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("agg")   # le rendu Agg mesure les textes ; savefig écrit du PDF
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.collections import PolyCollection  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from sklearn.decomposition import PCA  # noqa: E402

ICI = Path(__file__).resolve().parent
RACINE = ICI.parent.parent
NB_AXES = 6

# ─── Référentiels ───────────────────────────────────────────────────────────

# Acteurs dont on lit les mots d'ordre dans Swissvotes : clé → (libellé, colonnes).
# Le Centre a deux colonnes successives : PDC jusqu'à la fusion de 2021, puis
# « mitte » — on prend la première qui existe à la date de l'objet.
AUTORITES = {
    "CF": ("Conseil fédéral", ["br-pos"]),
    "Parlement": ("Parlement", ["bv-pos"]),
}
PARTIS = {
    "UDC": ("UDC", ["p-svp"]),
    "PLR": ("PLR", ["p-fdp"]),
    "Centre": ("Centre (PDC)", ["p-mitte", "p-cvp"]),
    "PBD": ("PBD", ["p-bdp"]),
    "PVL": ("PVL", ["p-glp"]),
    "PS": ("PS", ["p-sps"]),
    "Verts": ("Verts", ["p-gps"]),
    "PEV": ("PEV", ["p-evp"]),
    "UDF": ("UDF", ["p-edu"]),
    "Lega": ("Lega", ["p-lega"]),
    "MCG": ("MCG", ["p-mcg"]),
    "PST": ("PST-POP", ["p-pda"]),
}
ASSOCIATIONS = {
    "economiesuisse": ("economiesuisse", ["p-eco"]),
    "USAM": ("USAM (arts et métiers)", ["p-sgv"]),
    "UPS": ("Union patronale", ["p-sav"]),
    "USP": ("USP (paysans)", ["p-sbv"]),
    "USS": ("USS (syndicats)", ["p-sgb"]),
    "TravS": ("Travail.Suisse", ["p-travs"]),
    "Villes": ("Union des villes", ["p-ssv"]),
    "Cantons": ("Gouvernements cantonaux", ["p-kdk"]),
}
ACTEURS = {**AUTORITES, **PARTIS, **ASSOCIATIONS}
GRANDS_PARTIS = ["UDC", "PLR", "Centre", "PVL", "PS", "Verts"]
# Colonnes Swissvotes des sections cantonales dissidentes (pdev-<code>_<canton>).
CODE_DISSIDENCE = {"UDC": ["svp"], "PLR": ["fdp"], "Centre": ["mitte", "cvp"],
                   "PVL": ["glp"], "PS": ["sps"], "Verts": ["gps"]}
CAMP = {  # pour la couleur des acteurs dans les plans factoriels
    "UDC": 0, "UDF": 0, "Lega": 0, "MCG": 0, "USAM": 0,
    "PLR": 1, "Centre": 1, "PBD": 1, "PVL": 1, "PEV": 1, "CF": 1, "Parlement": 1,
    "economiesuisse": 1, "UPS": 1, "USP": 1, "Cantons": 1, "Villes": 1,
    "PS": 2, "Verts": 2, "PST": 2, "USS": 2, "TravS": 2,
}

TYPE = {1: "Référendum obligatoire", 2: "Référendum facultatif", 3: "Initiative populaire",
        4: "Contre-projet direct", 5: "Question subsidiaire"}
TYPE_COURT = {1: "RO", 2: "RF", 3: "IP", 4: "CP", 5: "QS"}
DOMAINES = {
    1: "Institutions", 2: "Politique extérieure", 3: "Sécurité", 4: "Économie",
    5: "Agriculture", 6: "Finances publiques", 7: "Énergie", 8: "Transports",
    9: "Environnement", 10: "Politique sociale", 11: "Formation", 12: "Culture, médias",
}
CANTONS = ["ZH", "BE", "LU", "UR", "SZ", "OW", "NW", "GL", "ZG", "FR", "SO", "BS", "BL",
           "SH", "AR", "AI", "SG", "GR", "AG", "TG", "TI", "VD", "VS", "NE", "GE", "JU"]
VILLES = ["Zürich", "Genève", "Basel", "Lausanne", "Bern", "Winterthur", "Luzern",
          "St. Gallen", "Lugano", "Biel/Bienne", "Fribourg", "Neuchâtel", "Sion",
          "Chur", "Zug", "La Chaux-de-Fonds", "Schwyz", "Appenzell", "Delémont"]

# Les trois facteurs de la rotation varimax des axes 1 à 3, une fois orientés
# (voir ``orienter_facteurs``) : c'est la lecture recommandée par le document.
FACTEURS = [
    {"cle": "F1", "nom": "Gauche – droite", "pole_neg": "droite", "pole_pos": "gauche"},
    {"cle": "F2", "nom": "Ouverture – souverainisme", "pole_neg": "souverainisme",
     "pole_pos": "ouverture"},
    {"cle": "F3", "nom": "Écologie et gauche alternative – bloc bourgeois",
     "pole_neg": "bloc bourgeois", "pole_pos": "écologie, gauche alternative"},
]

# Mots d'ordre du 27 septembre 2026 que Swissvotes n'avait pas encore saisis le
# 18.09.2026, complétés d'après la presse (RTS, « tous les partis sauf l'UDC
# rejettent l'initiative » ; Verts : liberté de vote sur l'alimentation).
PAROLES_COMPLEMENTAIRES = {
    6880: {"Centre": -1, "Verts": -1},
    6890: {"UDC": -1, "Centre": -1, "Verts": 0},
}

# ─── Charte (reprise de scrutin/charte.py, pour l'impression) ──────────────

ENCRE = "#1f1f1c"
ENCRE_2 = "#52514e"
MUET = "#898781"
GRILLE = "#e1e0d9"
BLEU, ROUGE, NEUTRE = "#2a78d6", "#c9352b", "#f0efec"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]          # trois premiers créneaux validés
COULEUR_LANGUE = {"allemand": "#2a78d6", "français": "#eb6834", "italien": "#1baf7a"}
AUTRE = "#b9b8b1"
POLICE = ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"]
DIVERGENTE = LinearSegmentedColormap.from_list("rouge_bleu", [ROUGE, NEUTRE, BLEU])

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": POLICE, "font.size": 8.5,
    "axes.edgecolor": "#c3c2b7", "axes.labelcolor": ENCRE_2, "axes.titlecolor": ENCRE,
    "xtick.color": MUET, "ytick.color": MUET, "axes.titlesize": 9.5,
    "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42,
})


# ─── Données ────────────────────────────────────────────────────────────────

@dataclass
class Base:
    communes: pd.DataFrame     # une ligne par commune retenue
    sujets: pd.DataFrame       # une ligne par objet, dans l'ordre des colonnes
    X: np.ndarray              # communes × objets, part de oui
    oui: np.ndarray            # communes × objets, voix
    non: np.ndarray
    pca_site: pd.DataFrame     # la table PCAResult telle que le site l'a calculée


def lire_base(chemin):
    """La matrice de ``getVotationMatrixWithMetaInfo``, lue directement dans SQLite.

    Une commune à qui il manque un objet est écartée, comme dans l'ACP du site.
    """
    con = sqlite3.connect(f"file:{chemin}?mode=ro", uri=True)
    communes = pd.read_sql(
        "select c.id, c.numero_ofs as ofs, c.nom, k.abreviation as canton, c.langue,"
        " c.degre_urbanisation as urbanisation, c.nb_voix as electeurs"
        " from scrutin_commune c join scrutin_canton k on k.id = c.canton_id", con)
    sujets = pd.read_sql("select id, sujet_id, date, nom from scrutin_sujetvote", con)
    res = pd.read_sql(
        "select commune_id, sujet_vote_id, nombre_oui, nombre_non"
        " from scrutin_resultatcommunalhistorique", con)
    pca_site = pd.read_sql("select * from pca_pcaresult", con)
    con.close()

    res = res[res.nombre_oui + res.nombre_non > 0]
    ids = sorted(res.sujet_vote_id.unique())
    oui = res.pivot(index="commune_id", columns="sujet_vote_id", values="nombre_oui")[ids].dropna()
    non = res.pivot(index="commune_id", columns="sujet_vote_id", values="nombre_non")[ids].loc[oui.index]
    sujets = sujets.set_index("id").loc[ids].reset_index()
    communes = communes.set_index("id").loc[oui.index].rename_axis("id").reset_index()
    oui, non = oui.values.astype(float), non.values.astype(float)
    sujets["oui_communes"] = oui.sum(0) / (oui + non).sum(0)
    return Base(communes, sujets, oui / (oui + non), oui, non, pca_site)


def lire_swissvotes(chemin, sujets):
    """Une ligne Swissvotes par objet, appariée par numéro (vorlagenId = 10 × anr)."""
    sv = pd.read_csv(chemin, sep=";", low_memory=False, encoding="utf-8-sig")
    sv["anr_num"] = pd.to_numeric(sv["anr"], errors="coerce")
    sv["date_sv"] = pd.to_datetime(sv["datum"], dayfirst=True).dt.strftime("%Y-%m-%d")
    s = sujets.assign(anr_num=sujets.sujet_id / 10)
    m = s.merge(sv, on="anr_num", how="left", validate="one_to_one")
    assert m.date_sv.notna().all(), "objet absent de Swissvotes"
    assert (m.date_sv == m.date).all(), "date différente entre Swissvotes et la base"
    return m


def lignes_swissvotes(chemin, numeros):
    """Les lignes Swissvotes d'objets absents de la base (le 27.09.2026)."""
    sv = pd.read_csv(chemin, sep=";", low_memory=False, encoding="utf-8-sig")
    sv["anr_num"] = pd.to_numeric(sv["anr"], errors="coerce")
    return sv[sv.anr_num.isin([n / 10 for n in numeros])].assign(
        sujet_id=lambda d: (d.anr_num * 10).round().astype(int))


def code_parole(valeur, subsidiaire=False):
    """Mot d'ordre Swissvotes → +1 (oui), −1 (non), 0 (liberté, blanc, pas de mot d'ordre).

    Dans une question subsidiaire, « oui » veut dire préférer l'initiative (code 9)
    et « non » le contre-projet (code 8), comme dans les résultats de l'OFS.
    ``None`` : l'acteur n'existait pas ou son mot d'ordre est inconnu.
    """
    v = pd.to_numeric(valeur, errors="coerce")
    if pd.isna(v) or v == 9999:
        return None
    v = int(v)
    if subsidiaire:
        return {9: 1, 8: -1, 1: 1, 2: -1}.get(v, 0)
    return {1: 1, 2: -1}.get(v, 0)


def paroles(m):
    """DataFrame objets × acteurs des mots d'ordre codés (+1, −1, 0, NaN)."""
    table = {}
    for cle, (_, colonnes) in ACTEURS.items():
        valeurs = []
        for _, ligne in m.iterrows():
            code = None
            for col in colonnes:
                code = code_parole(ligne[col], ligne["rechtsform"] == 5)
                if code is not None:
                    break
            valeurs.append(np.nan if code is None else code)
        table[cle] = valeurs
    return pd.DataFrame(table, index=m.sujet_id)


def dissidences(ligne, parole_nationale):
    """{parti: [sections cantonales qui ont pris le mot d'ordre contraire]}."""
    sortie = {}
    for parti, codes in CODE_DISSIDENCE.items():
        national = parole_nationale.get(parti)
        if national not in (1, -1):
            continue
        contraires = []
        for kt in CANTONS:
            for code in codes:
                v = pd.to_numeric(ligne.get(f"pdev-{code}_{kt}"), errors="coerce")
                if v in (1, 2) and (1 if v == 1 else -1) == -national:
                    contraires.append(kt)
                    break
        if contraires:
            sortie[parti] = contraires
    return sortie


def telecharger_swissvotes(dossier):
    """Jeu de données Swissvotes (CSV, séparateur « ; »), mis en cache tel quel."""
    url = "https://swissvotes.ch/page/dataset/swissvotes_dataset.csv"
    (Path(dossier) / "swissvotes_dataset.csv").write_bytes(urllib.request.urlopen(url, timeout=120).read())


def telecharger_force_partis(dossier, annees=("2023", "2019")):
    """Force des partis au Conseil national par commune, depuis STAT-TAB (réseau)."""
    url = ("https://www.pxweb.bfs.admin.ch/api/v1/fr/px-x-1702020000_105/"
           "px-x-1702020000_105.px")
    meta = json.load(urllib.request.urlopen(url))
    (Path(dossier) / "nr_meta.json").write_text(json.dumps(meta))
    var = {v["code"]: v for v in meta["variables"]}
    geo = next(v for code, v in var.items() if code.startswith("Bezirk"))
    for annee in annees:
        corps = {"query": [
            {"code": geo["code"], "selection": {"filter": "item", "values": geo["values"]}},
            {"code": "Jahr", "selection": {"filter": "item", "values": [annee]}},
            {"code": "Partei", "selection": {"filter": "item", "values": var["Partei"]["values"]}},
            {"code": "Ergebnisse", "selection": {"filter": "item", "values": ["2"]}},
        ], "response": {"format": "json"}}
        req = urllib.request.Request(url, data=json.dumps(corps).encode(),
                                     headers={"Content-Type": "application/json"})
        donnees = json.load(urllib.request.urlopen(req, timeout=600))
        (Path(dossier) / f"nr{annee}_force_partis_communes.json").write_text(json.dumps(donnees))


def lire_force_partis(dossier, annee="2023"):
    """DataFrame numéro OFS × parti de la force des partis en %, communes seulement."""
    meta = json.loads((Path(dossier) / "nr_meta.json").read_text())
    partis = next(v for v in meta["variables"] if v["code"] == "Partei")
    nom_parti = dict(zip(partis["values"], partis["valueTexts"]))
    donnees = json.loads((Path(dossier) / f"nr{annee}_force_partis_communes.json").read_text())
    lignes = []
    for cellule in donnees["data"]:
        geo, _, parti, _ = cellule["key"]
        if len(geo) != 4 or not geo.isdigit():
            continue          # district (6 chiffres)
        valeur = cellule["values"][0]
        force = float(valeur) if valeur not in ("...", "-", "") else 0.0
        lignes.append((int(geo), nom_parti[parti], force))
    table = pd.DataFrame(lignes, columns=["ofs", "parti", "force"])
    table = table.pivot(index="ofs", columns="parti", values="force").fillna(0.0)
    # Le Centre de 2023 réunit l'ancien PDC et le PBD ; les listes « PDC » et
    # « PBD » résiduelles y sont ajoutées. La gauche et la droite nationale
    # regroupent les petits partis de chaque bord.
    table["Centre"] = table["Centre"] + table.get("PDC", 0) + table.get("PBD", 0)
    table["Gauche"] = table["PS"] + table["Verts"] + table["PST"] + table["Sol."]
    table["Droite nationale"] = table["UDC"] + table["UDF"] + table["Lega"] + table["MCR"]
    return table


# ─── ACP ────────────────────────────────────────────────────────────────────

def acp_site(X, n=NB_AXES):
    """L'ACP de ``populate_pca`` : centrée, non réduite, communes non pondérées."""
    modele = PCA(n_components=n).fit(X)
    return modele, modele.transform(X)


def correlations(X, scores):
    """Corrélation objet × axe (le cercle des corrélations du site)."""
    k = X.shape[1]
    return np.nan_to_num(np.corrcoef(X, scores, rowvar=False)[:k, k:])


def acp_ponderee(X, poids, n=NB_AXES):
    """Variante B1 de PLAN_AMELIORATION_MODELE : centrage et SVD pondérés par la taille."""
    w = poids / poids.sum()
    mu = w @ X
    Xc = X - mu
    _, s, Vt = np.linalg.svd(np.sqrt(w)[:, None] * Xc, full_matrices=False)
    variance = s ** 2 / (s ** 2).sum()
    return Vt[:n], Xc @ Vt[:n].T, variance[:n]


def varimax(charges, gamma=1.0, iterations=200, tol=1e-10):
    """Rotation varimax (Kaiser) d'une matrice de charges objets × facteurs."""
    p, k = charges.shape
    R = np.eye(k)
    d = 0
    for _ in range(iterations):
        L = charges @ R
        u, s, vt = np.linalg.svd(charges.T @ (L ** 3 - (gamma / p) * L @ np.diag((L ** 2).sum(0))))
        R = u @ vt
        d_ancien, d = d, s.sum()
        if d_ancien != 0 and d / d_ancien < 1 + tol:
            break
    return charges @ R, R


def congruence(a, b):
    """Coefficient de congruence de Tucker entre deux vecteurs de charges."""
    return float(a @ b / np.sqrt((a @ a) * (b @ b)))


def projeter_acteurs(modele, X, table_paroles):
    """Chaque acteur comme une commune supplémentaire : oui = 100 %, non = 0 %.

    La liberté de vote vaut 50 %. Un mot d'ordre inconnu vaut la moyenne des
    communes, donc ne pèse sur aucun axe.
    """
    moyenne = X.mean(axis=0)
    positions = {}
    for acteur in table_paroles.columns:
        r = table_paroles[acteur].values
        x = np.where(np.isnan(r), moyenne, (r + 1) / 2)
        positions[acteur] = modele.transform(x[None, :])[0]
    return pd.DataFrame(positions).T


def r2(y, *colonnes):
    """R² d'une régression linéaire avec constante."""
    A = np.column_stack([np.ones(len(y)), *colonnes])
    b, *_ = np.linalg.lstsq(A, y, rcond=None)
    e = y - A @ b
    return float(1 - e.var() / y.var())


def indicatrices(serie):
    """Indicatrices d'une variable qualitative, sans la première modalité."""
    return pd.get_dummies(serie.fillna("?")).astype(float).values[:, 1:]


# ─── Analyses ───────────────────────────────────────────────────────────────

def orienter_facteurs(R, positions_rot):
    """Oriente les facteurs tournés : F1 + = PS, F2 + = PLR, F3 + = Verts."""
    for f, (acteur, _) in enumerate([("PS", 1), ("PLR", 1), ("Verts", 1)]):
        if f < R.shape[1] and positions_rot.loc[acteur].iloc[f] < 0:
            R[:, f] *= -1
    return R


def rotation(C, scores, positions, n):
    """Varimax sur les ``n`` premiers axes : charges, scores et acteurs tournés, orientés."""
    _, R = varimax(C[:, :n])
    et = scores[:, :n].std(0)
    pos = positions.iloc[:, :n] / et
    R = orienter_facteurs(R, pos @ R)
    return {"R": R, "charges": C[:, :n] @ R, "scores": (scores[:, :n] / et) @ R,
            "acteurs": pos @ R}


def motif_coalition(p):
    """Configuration des mots d'ordre des six grands partis face au Conseil fédéral."""
    cf = p["CF"]
    contre = {q for q in GRANDS_PARTIS if p[q] == -cf}
    if not contre:
        return "Tous avec le Conseil fédéral"
    if contre == {"UDC"}:
        return "UDC seule contre"
    if contre <= {"PS", "Verts"}:
        return "Gauche seule contre"
    if contre <= {"PS", "Verts", "PVL"}:
        return "Gauche et PVL contre"
    if "UDC" in contre and contre & {"PS", "Verts"}:
        return "UDC et gauche contre"
    if "UDC" in contre:
        return "UDC et une partie du centre-droit contre"
    return "Centre-droit divisé"


def extremes_communes(communes, valeurs, n=8, electeurs_min=800):
    """Communes les plus basses et les plus hautes (hors Suisses de l'étranger)."""
    c = communes.assign(v=valeurs)
    c = c[(c.ofs < 9000) & (c.electeurs >= electeurs_min)].sort_values("v")
    fmt = lambda d: [{"nom": r.nom, "canton": r.canton, "v": round(r.v, 2)} for r in d.itertuples()]  # noqa: E731
    return {"bas": fmt(c.head(n)), "haut": fmt(c.tail(n).iloc[::-1])}


def moyennes(communes, valeurs, colonne):
    c = communes.assign(v=valeurs)
    c = c[c.ofs < 9000]
    return {str(k): round(float(v), 3) for k, v in c.groupby(colonne)["v"].mean().items()}


def analyser(base, sv, sources):
    communes, sujets, X = base.communes, base.sujets, base.X
    modele, scores = acp_site(X)
    C = correlations(X, scores)
    variance = PCA(n_components=10).fit(X).explained_variance_ratio_

    # Contrôle : on interprète bien les axes du site.
    site = base.pca_site.set_index("commune_id").loc[communes.id]
    reproduction = [float(np.corrcoef(scores[:, k], site[f"coordinate_{k + 1}"])[0, 1])
                    for k in range(NB_AXES)]
    ecart = float(np.abs(scores - site[[f"coordinate_{k + 1}" for k in range(NB_AXES)]].values).max())

    P = paroles(sv)
    positions = projeter_acteurs(modele, X, P)
    rot2 = rotation(C, scores, positions, 2)
    rot3 = rotation(C, scores, positions, 3)
    rot6 = rotation(C, scores, positions, 6)
    angle = float(np.degrees(np.arctan2(rot2["R"][1, 0], rot2["R"][0, 0])))

    # ── Côté objets : qui soutient quoi ──
    alignement = {}
    for a in P.columns:
        r = P[a].values
        ok = np.isin(r, [-1, 1])
        alignement[a] = {"n": int(ok.sum()), "axes": [
            float(np.corrcoef(r[ok], C[ok, k])[0, 1]) if ok.sum() > 12 else None
            for k in range(NB_AXES)]}
    Pz = P.fillna(0)
    initiative = (sv.rechtsform.values == 3).astype(float)
    domaine = indicatrices(pd.to_numeric(sv.d1e1, errors="coerce").astype(int).map(DOMAINES))
    modeles_objets = {
        "Mot d'ordre UDC": [Pz["UDC"].values],
        "Mot d'ordre PS": [Pz["PS"].values],
        "Mot d'ordre PLR": [Pz["PLR"].values],
        "Mot d'ordre Verts": [Pz["Verts"].values],
        "Position du Conseil fédéral": [Pz["CF"].values],
        "Mot d'ordre USP (paysans)": [Pz["USP"].values],
        "Initiative (ou non)": [initiative],
        "Domaine politique": [domaine],
        "UDC + PS": [Pz["UDC"].values, Pz["PS"].values],
        "Six grands partis": [Pz[p].values for p in GRANDS_PARTIS],
        "Six partis + Conseil fédéral + domaine": [Pz[p].values for p in GRANDS_PARTIS + ["CF"]] + [domaine],
    }
    r2_objets = {nom: [r2(C[:, k], *cols) for k in range(NB_AXES)]
                 for nom, cols in modeles_objets.items()}
    r2_objets_rot = {nom: [r2(rot3["charges"][:, k], *cols) for k in range(3)]
                     for nom, cols in modeles_objets.items()}

    motifs = pd.Series([motif_coalition(P.iloc[i]) for i in range(len(P))])
    tab_motifs = []
    for motif, idx in motifs.groupby(motifs).groups.items():
        idx = list(idx)
        tab_motifs.append({
            "motif": motif, "n": len(idx),
            "axes": [float((C[idx, k] ** 2).mean()) for k in range(3)],
            "facteurs": [float((rot3["charges"][idx, k] ** 2).mean()) for k in range(3)],
            "initiatives": float(initiative[idx].mean()),
        })
    tab_motifs.sort(key=lambda d: -d["n"])

    # ── Côté communes ──
    suivi = {}
    for a in ["UDC", "PLR", "Centre", "PVL", "PS", "Verts", "CF", "economiesuisse", "USP", "USS"]:
        r = P[a].values
        ok = np.isin(r, [-1, 1])
        indice = np.where(r[ok] == 1, X[:, ok], 1 - X[:, ok]).mean(1)
        suivi[a] = {"moyenne": float(indice.mean()),
                    "axes": [float(np.corrcoef(indice, scores[:, k])[0, 1]) for k in range(NB_AXES)],
                    "facteurs": [float(np.corrcoef(indice, rot3["scores"][:, k])[0, 1]) for k in range(3)]}

    force = lire_force_partis(sources)
    avec_force = communes.merge(force, left_on="ofs", right_index=True, how="left")
    ok = avec_force["UDC"].notna().values
    colonnes_partis = ["UDC", "PLR", "Centre", "PVL", "PS", "Verts", "Gauche",
                       "Droite nationale", "Lega", "MCR"]
    corr_force = {p: {"axes": [float(np.corrcoef(avec_force.loc[ok, p], scores[ok, k])[0, 1])
                               for k in range(NB_AXES)],
                      "facteurs": [float(np.corrcoef(avec_force.loc[ok, p], rot3["scores"][ok, k])[0, 1])
                                   for k in range(3)]}
                  for p in colonnes_partis}
    M_partis = avec_force.loc[ok, ["UDC", "PLR", "Centre", "PVL", "PS", "Verts", "Lega", "MCR"]].values
    langue = indicatrices(avec_force.loc[ok, "langue"])
    urbain = indicatrices(avec_force.loc[ok, "urbanisation"])
    taille = np.log(avec_force.loc[ok, "electeurs"].clip(lower=1)).values
    modeles_communes = {
        "Force des partis (2023)": [M_partis],
        "Langue": [langue],
        "Degré d'urbanisation": [urbain],
        "Taille (log des électeurs)": [taille],
        "Langue + urbanisation + taille": [langue, urbain, taille],
        "Partis + langue + urbanisation + taille": [M_partis, langue, urbain, taille],
    }
    r2_communes = {nom: [r2(scores[ok, k], *cols) for k in range(NB_AXES)]
                   for nom, cols in modeles_communes.items()}
    r2_communes_rot = {nom: [r2(rot3["scores"][ok, k], *cols) for k in range(3)]
                       for nom, cols in modeles_communes.items()}

    axes = []
    for k in range(NB_AXES):
        ordre = np.argsort(C[:, k])
        axes.append({
            "numero": k + 1,
            "variance": float(modele.explained_variance_ratio_[k]),
            "ecart_type": float(scores[:, k].std()),
            "objets_bas": [int(sujets.sujet_id[j]) for j in ordre[:10]],
            "objets_haut": [int(sujets.sujet_id[j]) for j in ordre[::-1][:10]],
            "communes": extremes_communes(communes, scores[:, k]),
            "langue": moyennes(communes, scores[:, k], "langue"),
            "urbanisation": moyennes(communes, scores[:, k], "urbanisation"),
            "canton": moyennes(communes, scores[:, k], "canton"),
        })
    facteurs = []
    for k, f in enumerate(FACTEURS):
        ordre = np.argsort(rot3["charges"][:, k])
        facteurs.append({
            **f,
            # La rotation redistribue la variance des trois premiers axes : chaque
            # facteur en reçoit une part proportionnelle à ses charges au carré.
            "variance": float((rot3["charges"][:, k] ** 2).sum() / (C[:, :3] ** 2).sum()
                              * modele.explained_variance_ratio_[:3].sum()),
            "objets_bas": [int(sujets.sujet_id[j]) for j in ordre[:10]],
            "objets_haut": [int(sujets.sujet_id[j]) for j in ordre[::-1][:10]],
            "communes": extremes_communes(communes, rot3["scores"][:, k]),
            "langue": moyennes(communes, rot3["scores"][:, k], "langue"),
            "urbanisation": moyennes(communes, rot3["scores"][:, k], "urbanisation"),
            "canton": moyennes(communes, rot3["scores"][:, k], "canton"),
            "congruence_axes": [congruence(rot3["charges"][:, k], C[:, j]) for j in range(3)],
        })

    villes = []
    for nom in VILLES:
        ligne = communes[(communes.nom == nom) & (communes.ofs < 9000)]
        if len(ligne):
            i = ligne.index[0]
            villes.append({"nom": nom, "canton": ligne.canton.iloc[0],
                           "axes": [round(float(scores[i, k]), 2) for k in range(NB_AXES)],
                           "facteurs": [round(float(rot3["scores"][i, k]), 2) for k in range(3)]})

    # ── Robustesse ──
    robustesse = {}
    poids = communes.electeurs.clip(lower=1).values.astype(float)
    Vw, _, var_w = acp_ponderee(X, poids)
    robustesse["ponderee"] = {"variance": var_w.tolist(),
                              "congruence": [[abs(congruence(modele.components_[i], Vw[j]))
                                              for j in range(NB_AXES)] for i in range(NB_AXES)]}
    Xs = (X - X.mean(0)) / X.std(0)
    reduite = PCA(NB_AXES).fit(Xs)
    Ss = reduite.transform(Xs)
    robustesse["reduite"] = {"variance": reduite.explained_variance_ratio_.tolist(),
                             "correlation": np.abs(np.corrcoef(scores.T, Ss.T)[:NB_AXES, NB_AXES:]).tolist()}
    dates = pd.to_datetime(sujets.date)
    robustesse["periodes"] = {}
    for nom, masque in [("2014-2019", dates < "2020-01-01"), ("2020-2026", dates >= "2020-01-01")]:
        mp = PCA(NB_AXES).fit(X[:, masque.values])
        Sp = mp.transform(X[:, masque.values])
        robustesse["periodes"][nom] = {
            "objets": int(masque.sum()), "variance": mp.explained_variance_ratio_.tolist(),
            "correlation": np.abs(np.corrcoef(scores.T, Sp.T)[:NB_AXES, NB_AXES:]).tolist(),
            "facteurs": np.abs(np.corrcoef(rot3["scores"].T, Sp[:, :3].T)[:3, 3:]).tolist(),
        }
    robustesse["varimax6"] = {
        "variance": ((rot6["charges"] ** 2).sum(0) / X.shape[1]).tolist(),
        "congruence_axes": [[congruence(rot6["charges"][:, i], C[:, j]) for j in range(NB_AXES)]
                            for i in range(NB_AXES)],
        "objets_haut": [[int(sujets.sujet_id[j]) for j in np.argsort(-np.abs(rot6["charges"][:, i]))[:8]]
                        for i in range(NB_AXES)],
        "charges": rot6["charges"].tolist(),
    }

    return {
        "modele": modele, "scores": scores, "C": C, "variance10": variance, "P": P,
        "positions": positions, "rot2": rot2, "rot3": rot3, "rot6": rot6, "angle": angle,
        "reproduction": reproduction, "ecart": ecart, "alignement": alignement,
        "r2_objets": r2_objets, "r2_objets_rot": r2_objets_rot, "motifs": motifs,
        "tab_motifs": tab_motifs, "suivi": suivi, "corr_force": corr_force,
        "r2_communes": r2_communes, "r2_communes_rot": r2_communes_rot,
        "sans_force": int((~ok).sum()), "axes": axes, "facteurs": facteurs,
        "villes": villes, "robustesse": robustesse,
    }


def stabilite_ajout(base, base_avant):
    """Les axes changent-ils quand un scrutin s'ajoute ? Corrélation signée des scores."""
    _, s1 = acp_site(base.X)
    _, s0 = acp_site(base_avant.X)
    commun = base.communes.reset_index().merge(base_avant.communes.reset_index(), on="id",
                                               suffixes=("", "_avant"))
    a, b = s1[commun["index"].values], s0[commun["index_avant"].values]
    return {"objets_avant": int(base_avant.X.shape[1]),
            "correlation": np.corrcoef(a.T, b.T)[:NB_AXES, NB_AXES:].tolist()}


def fiches_objets(base, sv, res, textes):
    """Une entrée par objet : textes, résultat, mots d'ordre, géographie, axes."""
    communes, X = base.communes, base.X
    C, P, rot3 = res["C"], res["P"], res["rot3"]
    groupes = {
        "romandie": (communes.langue == "français").values,
        "alemanique": (communes.langue == "allemand").values,
        "italophone": (communes.langue == "italien").values,
        "urbain": (communes.urbanisation == "urbain").values,
        "rural": (communes.urbanisation == "rural").values,
    }
    par_canton = {kt: (communes.canton == kt).values for kt in CANTONS}
    dimension = np.argmax(rot3["charges"] ** 2, axis=1)
    objets = []
    for i, ligne in sv.iterrows():
        sid = int(ligne.sujet_id)
        texte = textes.loc[sid]
        p = {a: (None if pd.isna(P.iloc[i][a]) else int(P.iloc[i][a])) for a in P.columns}
        # Résultat cantonal recalculé depuis les communes (Suisses de l'étranger
        # compris) : Swissvotes ne l'a pas encore pour les objets récents.
        japroz = {kt: round(100 * float(base.oui[m, i].sum() / (base.oui[m, i] + base.non[m, i]).sum()), 1)
                  for kt, m in par_canton.items()}
        oui_groupes = {g: float(base.oui[m, i].sum() / (base.oui[m, i] + base.non[m, i]).sum())
                       for g, m in groupes.items()}
        kt_ja = pd.to_numeric(ligne["kt-ja"], errors="coerce")
        kt_nein = pd.to_numeric(ligne["kt-nein"], errors="coerce")
        objets.append({
            "sujet_id": sid, "date": ligne.date, "titre": texte.titre, "etiquette": texte.etiquette,
            "theme": texte.theme, "enjeu": texte.enjeu, "titre_officiel": ligne.nom,
            "type": TYPE[int(ligne.rechtsform)], "type_court": TYPE_COURT[int(ligne.rechtsform)],
            "auteur": None if str(ligne["urheber-fr"]) in ("nan", ".") else str(ligne["urheber-fr"]),
            "domaine": DOMAINES.get(int(pd.to_numeric(ligne.d1e1, errors="coerce")), "?"),
            "oui": float(ligne["volkja-proz"]) / 100,
            "cantons_oui": None if pd.isna(kt_ja) else float(kt_ja),
            "cantons_non": None if pd.isna(kt_nein) else float(kt_nein),
            "accepte": str(ligne.annahme) == "1",
            "paroles": p, "motif": res["motifs"].iloc[i],
            "dissidences": dissidences(ligne, p),
            "cantons_extremes": sorted(japroz.items(), key=lambda kv: kv[1]),
            "groupes": oui_groupes,
            "axes": [round(float(C[i, k]), 3) for k in range(NB_AXES)],
            "facteurs": [round(float(rot3["charges"][i, k]), 3) for k in range(3)],
            "dimension": int(dimension[i]),
            "qualite": float((C[i] ** 2).sum()),
            "ecart_type_communes": float(X[:, i].std()),
        })
    return objets


def objets_du_jour(res, sv, sv_futur):
    """Où tomberont les objets du 27.09.2026 ? Prédiction par les mots d'ordre.

    Régression, sur les 103 objets connus, de la corrélation avec chaque axe (et
    chaque facteur tourné) sur les mots d'ordre du Conseil fédéral et des six
    grands partis ; puis les trois objets historiques les plus proches par les
    mots d'ordre et le domaine.
    """
    P = res["P"]
    acteurs = ["CF"] + GRANDS_PARTIS
    A = np.column_stack([np.ones(len(P))] + [P[a].fillna(0).values for a in acteurs])
    cibles = np.column_stack([res["C"][:, :3], res["rot3"]["charges"]])
    B, *_ = np.linalg.lstsq(A, cibles, rcond=None)
    sortie = []
    for _, ligne in sv_futur.iterrows():
        sid = int(ligne.sujet_id)
        p = {}
        for a in acteurs:
            code = None
            for col in ACTEURS[a][1]:
                code = code_parole(ligne[col])
                if code is not None:
                    break
            p[a] = code
        p.update(PAROLES_COMPLEMENTAIRES.get(sid, {}))
        x = np.array([1.0] + [p[a] if p[a] is not None else 0.0 for a in acteurs])
        prediction = x @ B
        # Voisins : mots d'ordre les plus proches, un domaine politique différent
        # comptant comme deux mots d'ordre de différence.
        v = np.array([p[a] if p[a] is not None else 0.0 for a in acteurs])
        domaine = int(pd.to_numeric(ligne.d1e1, errors="coerce"))
        autre_domaine = pd.to_numeric(sv.d1e1, errors="coerce").values.astype(int) != domaine
        distance = np.abs(P[acteurs].fillna(0).values - v).sum(1) + 2 * autre_domaine
        ordre = np.argsort(distance, kind="stable")
        sortie.append({
            "sujet_id": sid, "titre": ligne.titel_kurz_f, "paroles": p,
            "axes": prediction[:3].tolist(), "facteurs": prediction[3:].tolist(),
            "voisins": [int(P.index[j]) for j in ordre[:6]],
            "domaine": DOMAINES.get(domaine, "?"),
        })
    return sortie


# ─── Figures ────────────────────────────────────────────────────────────────

def _polygones(geojson):
    """{numéro OFS: [anneaux extérieurs en coordonnées projetées]} et le cadre."""
    kappa = np.cos(np.radians(46.8))
    formes = {}
    for f in geojson["features"]:
        g = f["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        cle = f["properties"].get("vogeId", f["properties"].get("nom"))
        formes.setdefault(cle, []).extend(
            [np.column_stack([np.array(p[0])[:, 0] * kappa, np.array(p[0])[:, 1]]) for p in polys])
    return formes


def carte(ax, formes, lacs, valeurs, titre, borne=None, legende=None, taille_legende=7.5):
    """Choroplèthe divergente centrée sur 0, bornée à ± 2,5 écarts-types."""
    borne = borne or 2.5 * np.nanstd(list(valeurs.values()))
    polys, couleurs = [], []
    for ofs, anneaux in formes.items():
        v = valeurs.get(ofs)
        c = AUTRE if v is None else DIVERGENTE(0.5 + 0.5 * np.clip(v / borne, -1, 1))
        for a in anneaux:
            polys.append(a)
            couleurs.append(c)
    ax.add_collection(PolyCollection(polys, facecolors=couleurs, edgecolors=couleurs, linewidths=0.05))
    lac = [a for anneaux in lacs.values() for a in anneaux]
    ax.add_collection(PolyCollection(lac, facecolors="#ffffff", edgecolors="#c3c2b7", linewidths=0.2))
    ax.autoscale_view()
    ax.set_aspect("equal")
    ax.axis("off")
    if titre:
        ax.set_title(titre, loc="left", fontsize=9, color=ENCRE)
    if legende:
        bas, haut = legende
        ax.text(0.0, -0.02, f"En rouge : {bas}", transform=ax.transAxes, ha="left", va="top",
                fontsize=taille_legende, color=ROUGE)
        ax.text(1.0, -0.02, f"en bleu : {haut}", transform=ax.transAxes, ha="right", va="top",
                fontsize=taille_legende, color=BLEU)


def figure_cartes(res, base, contours, dossier):
    formes = _polygones(json.loads((contours / "communes.geojson").read_text()))
    lacs = _polygones(json.loads((contours / "lacs.geojson").read_text()))
    ofs = base.communes.ofs.values
    poles = {1: ("UDC, fermeture", "gauche, ouverture"),
             2: ("camp gouvernemental", "contestation"),
             3: ("bloc bourgeois", "gauche alternative, écologie"),
             4: ("protestant", "catholique"), 5: ("Tessin", "Grisons, montagne"),
             6: ("Mittelland industriel", "paysans de montagne")}
    for k in range(NB_AXES):
        taille = (7.2, 4.6) if k < 3 else (3.5, 2.35)
        fig, ax = plt.subplots(figsize=taille)
        carte(ax, formes, lacs, dict(zip(ofs, res["scores"][:, k])), None,
              legende=poles[k + 1] if k < 3 else None)
        fig.savefig(dossier / f"carte_axe{k + 1}.png", bbox_inches="tight", pad_inches=0.02, dpi=300)
        plt.close(fig)
    for k, f in enumerate(FACTEURS):
        # Les cartes des facteurs se lisent deux par deux, côte à côte.
        fig, ax = plt.subplots(figsize=(3.6, 2.35))
        carte(ax, formes, lacs, dict(zip(ofs, res["rot3"]["scores"][:, k])), None,
              legende=(f["pole_neg"], f["pole_pos"]), taille_legende=6.5)
        fig.savefig(dossier / f"carte_F{k + 1}.png", bbox_inches="tight", pad_inches=0.02, dpi=300)
        plt.close(fig)


def figure_eboulis(res, dossier):
    v = res["variance10"] * 100
    fig, ax = plt.subplots(figsize=(6.4, 2.2))
    couleurs = [BLEU if k < NB_AXES else AUTRE for k in range(len(v))]
    ax.bar(np.arange(1, len(v) + 1), v, color=couleurs, width=0.62)
    for k, val in enumerate(v):
        ax.text(k + 1, val + 0.8, f"{val:.1f}".replace(".", ","), ha="center", fontsize=7.5, color=ENCRE_2)
    ax.set_xticks(np.arange(1, len(v) + 1))
    ax.set_xlabel("Axe (en bleu : les six que garde le site)")
    ax.set_ylabel("Variance expliquée (%)")
    ax.set_ylim(0, v[0] * 1.15)
    ax.grid(axis="y", color=GRILLE, linewidth=0.5)
    ax.set_axisbelow(True)
    fig.savefig(dossier / "eboulis.pdf", bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)


def _etiqueter(ax, points, textes, tailles, gras, decalage=4.0, iterations=400):
    """Étiquettes sans chevauchement, placées d'après leur taille réelle.

    Chaque étiquette part à côté de son point (à droite, ou à gauche si elle
    sortirait du cadre), puis celles qui se recouvrent s'écartent verticalement
    jusqu'à ne plus se toucher. Un filet relie au point une étiquette qui s'en
    est éloignée. Les limites des axes doivent être fixées avant l'appel.
    """
    rendu = ax.figure.canvas.get_renderer()
    vers_ecran, vers_donnees = ax.transData, ax.transData.inverted()
    xy = vers_ecran.transform(np.asarray(points, dtype=float))
    cadre = ax.get_window_extent(rendu)
    textes_mpl = [ax.text(0, 0, t, fontsize=tailles[k], color=ENCRE, va="center", ha="left",
                          fontweight="bold" if gras[k] else "normal", zorder=5)
                  for k, t in enumerate(textes)]
    boites = [t.get_window_extent(rendu) for t in textes_mpl]
    larg = np.array([b.width for b in boites])
    haut = np.array([b.height for b in boites])
    pos = xy.copy()
    a_gauche = xy[:, 0] + decalage + larg > cadre.x1
    pos[:, 0] = np.where(a_gauche, xy[:, 0] - decalage - larg, xy[:, 0] + decalage)
    for _ in range(iterations):
        bouge = False
        for i in range(len(pos)):
            for j in range(i + 1, len(pos)):
                if pos[i, 0] < pos[j, 0] + larg[j] and pos[j, 0] < pos[i, 0] + larg[i]:
                    besoin = (haut[i] + haut[j]) / 2 + 1.0
                    dy = abs(pos[i, 1] - pos[j, 1])
                    if dy < besoin:
                        d = (besoin - dy) / 2 + 0.3
                        s = 1 if pos[i, 1] >= pos[j, 1] else -1
                        pos[i, 1] += s * d
                        pos[j, 1] -= s * d
                        bouge = True
        if not bouge:
            break
    for k, t in enumerate(textes_mpl):
        t.set_position(vers_donnees.transform(pos[k]))
        if abs(pos[k, 1] - xy[k, 1]) > 0.6 * haut[k]:
            bord = pos[k] + ([larg[k], 0] if a_gauche[k] else [0, 0])
            (x0, y0), (x1, y1) = vers_donnees.transform(xy[k]), vers_donnees.transform(bord)
            ax.plot([x0, x1], [y0, y1], color="#c3c2b7", lw=0.5, zorder=4)


def _nuage_communes(ax, Z, communes):
    """Les communes en fond, une couleur par région linguistique."""
    for langue, couleur in list(COULEUR_LANGUE.items()) + [(None, AUTRE)]:
        m = (communes.langue == langue).values if langue else ~communes.langue.isin(COULEUR_LANGUE).values
        ax.scatter(Z[m, 0], Z[m, 1], s=3, color=couleur, alpha=0.35, linewidths=0,
                   label=langue.capitalize() if langue else "Romanche, Suisses de l'étranger")


def _acteurs(ax, positions):
    """Les acteurs, à l'encre : grands partis et Conseil fédéral en gras."""
    acteurs = [a for a in positions.index if a != "Parlement"]
    grands = [a in GRANDS_PARTIS or a == "CF" for a in acteurs]
    xy = positions.loc[acteurs].values[:, :2]
    ax.scatter(xy[:, 0], xy[:, 1], s=[28 if g else 12 for g in grands], color=ENCRE,
               edgecolors="white", linewidths=0.8, zorder=3)
    _etiqueter(ax, xy, [ACTEURS[a][0] for a in acteurs],
               [8.2 if g else 6.8 for g in grands], grands)


def _legende_dessous(ax, titre=None, y=-0.11, echelle=3):
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, y), ncol=4, fontsize=6.8,
              frameon=False, markerscale=echelle, title=titre, title_fontsize=6.8)


def figure_plan_acteurs(res, base, dossier, i=0, j=1, nom="partis_plan12"):
    """Communes (points) et acteurs (étiquettes) dans le plan de deux axes du site."""
    s = res["scores"]
    pos = res["positions"].iloc[:, [i, j]]
    fig, ax = plt.subplots(figsize=(7.0, 5.6))
    _nuage_communes(ax, s[:, [i, j]], base.communes)
    lim_x = np.abs(pos.values[:, 0]).max() * 1.2
    lim_y = np.abs(pos.values[:, 1]).max() * 1.2
    ax.set_xlim(-lim_x, lim_x)
    ax.set_ylim(-lim_y, lim_y)
    ax.axhline(0, color=GRILLE, lw=0.6, zorder=0)
    ax.axvline(0, color=GRILLE, lw=0.6, zorder=0)
    if (i, j) == (0, 1):
        # Directions des deux facteurs de la rotation, dans le plan des scores.
        R, et = res["rot2"]["R"], s[:, :2].std(0)
        for f, (neg, posi) in enumerate([("droite", "gauche"), ("souverainisme", "ouverture")]):
            d = R[:, f] * et
            d = d / np.abs(d / [lim_x, lim_y]).max() * 0.97
            ax.plot([-d[0], d[0]], [-d[1], d[1]], color=MUET, lw=0.7, ls=(0, (4, 3)), zorder=1)
            ax.text(*(d * 0.97), posi, fontsize=7.5, color=MUET, style="italic",
                    ha="right" if d[0] > 0 else "left", va="bottom" if d[1] > 0 else "top")
            ax.text(*(-d * 0.97), neg, fontsize=7.5, color=MUET, style="italic",
                    ha="left" if d[0] > 0 else "right", va="top" if d[1] > 0 else "bottom")
    _acteurs(ax, pos)
    ax.set_xlabel(f"Axe {i + 1}")
    ax.set_ylabel(f"Axe {j + 1}")
    _legende_dessous(ax)
    fig.savefig(dossier / f"{nom}.pdf", bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)


def figure_plan_facteurs(res, base, dossier):
    """Le plan tourné : communes par langue, acteurs, et les quatre quadrants."""
    Z, A = res["rot2"]["scores"], res["rot2"]["acteurs"]
    fig, ax = plt.subplots(figsize=(7.0, 5.8))
    _nuage_communes(ax, Z, base.communes)
    lim = np.abs(A.values).max() * 1.2
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.axhline(0, color=GRILLE, lw=0.6, zorder=0)
    ax.axvline(0, color=GRILLE, lw=0.6, zorder=0)
    for (x, y, texte, ha, va) in [(-lim, lim, "droite ouverte", "left", "top"),
                                  (lim, lim, "gauche ouverte", "right", "top"),
                                  (-lim, -lim, "droite souverainiste", "left", "bottom"),
                                  (lim, -lim, "gauche souverainiste", "right", "bottom")]:
        ax.text(x * 0.98, y * 0.98, texte, ha=ha, va=va, fontsize=8, color=MUET, style="italic")
    _acteurs(ax, A)
    ax.set_xlabel("F1, gauche – droite (en écarts-types ; la gauche à droite du graphique)")
    ax.set_ylabel("F2, ouverture – souverainisme (l'ouverture en haut)")
    _legende_dessous(ax)
    fig.savefig(dossier / "plan_facteurs.pdf", bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)


def _colonnes(ax, points, textes, x_colonne=1.1, taille=6.4):
    """Étiquettes rangées en deux colonnes de part et d'autre du cercle.

    Chaque étiquette garde la hauteur de son point autant que possible ; deux
    passes (vers le bas puis vers le haut) imposent l'interligne minimal.
    """
    rendu = ax.figure.canvas.get_renderer()
    cadre = ax.get_window_extent(rendu)
    y0, y1 = ax.get_ylim()
    interligne = taille * 1.25 / 72 * ax.figure.dpi * (y1 - y0) / cadre.height
    for cote in (1, -1):
        idx = [k for k in range(len(points)) if np.sign(points[k][0] or 1) == cote]
        idx.sort(key=lambda k: -points[k][1])
        ys = [points[k][1] for k in idx]
        for n in range(1, len(ys)):
            ys[n] = min(ys[n], ys[n - 1] - interligne)
        ys[-1] = max(ys[-1], y0 + interligne) if ys else None
        for n in range(len(ys) - 2, -1, -1):
            ys[n] = max(ys[n], ys[n + 1] + interligne)
        for k, y in zip(idx, ys):
            x, yp = points[k]
            xc = cote * x_colonne
            ax.plot([x, cote * (abs(x) + 0.03), xc - cote * 0.02], [yp, yp, y],
                    color="#c3c2b7", lw=0.45, zorder=1)
            ax.text(xc, y, textes[k], fontsize=taille, color=ENCRE_2, va="center",
                    ha="left" if cote > 0 else "right")


def figure_cercle(res, objets, dossier, i=0, j=1, nom="cercle12", n_etiquettes=32, rot=None):
    """Cercle des corrélations, couleur = facteur dominant de la rotation à trois."""
    if rot is None:
        cx, cy = res["C"][:, i], res["C"][:, j]
        lx, ly = f"Axe {i + 1}", f"Axe {j + 1}"
    else:
        cx, cy = rot[:, i], rot[:, j]
        lx = f"{FACTEURS[i]['nom']} (à droite : {FACTEURS[i]['pole_pos']})"
        ly = f"{FACTEURS[j]['nom']} (en haut : {FACTEURS[j]['pole_pos']})"
    dim = np.array([o["dimension"] for o in objets])
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    ax.set_xlim(-2.05, 2.05)
    ax.set_ylim(-1.12, 1.12)
    ax.set_aspect("equal")
    t = np.linspace(0, 2 * np.pi, 300)
    ax.plot(np.cos(t), np.sin(t), color=GRILLE, lw=0.8)
    ax.plot([-1, 1], [0, 0], color=GRILLE, lw=0.6)
    ax.plot([0, 0], [-1, 1], color=GRILLE, lw=0.6)
    for f in range(3):
        m = dim == f
        ax.scatter(cx[m], cy[m], s=15, color=SERIES[f], edgecolors="white", linewidths=0.6,
                   label=FACTEURS[f]["nom"], zorder=3)
    # Les objets les plus extrêmes vers chacun des quatre pôles, pour équilibrer
    # les deux colonnes d'étiquettes.
    choix = []
    for v in (cx, -cx, cy, -cy):
        choix += [k for k in np.argsort(-v)[:n_etiquettes // 4] if k not in choix]
    _colonnes(ax, [(cx[k], cy[k]) for k in choix], [objets[k]["etiquette"] for k in choix])
    for cote in ("top", "right", "left", "bottom"):
        ax.spines[cote].set_visible(False)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.text(0, -1.1, f"Horizontalement : {lx}. Verticalement : {ly}.", fontsize=7.2,
            color=ENCRE_2, ha="center", va="top")
    _legende_dessous(ax, "Couleur : facteur dominant après rotation", y=0.0, echelle=1.2)
    fig.savefig(dossier / f"{nom}.pdf", bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)


# ─── Sortie ─────────────────────────────────────────────────────────────────

def _json(obj):
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    raise TypeError(type(obj))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", default=RACINE / "var/reel-veille.sqlite3", type=Path)
    parser.add_argument("--base-avant", default=RACINE / "var/juin-1815.sqlite3", type=Path,
                        help="la même base sans le dernier scrutin, pour la stabilité (facultative)")
    parser.add_argument("--sources", default=RACINE / "var/sources", type=Path)
    parser.add_argument("--contours", default=RACINE / "carte/static/carte", type=Path)
    parser.add_argument("--telecharger", action="store_true",
                        help="rafraîchir Swissvotes et la force des partis (réseau)")
    args = parser.parse_args()

    if args.telecharger:
        args.sources.mkdir(parents=True, exist_ok=True)
        telecharger_swissvotes(args.sources)
        telecharger_force_partis(args.sources)
    base = lire_base(args.base)
    sv = lire_swissvotes(args.sources / "swissvotes_dataset.csv", base.sujets)
    res = analyser(base, sv, args.sources)
    textes = pd.read_csv(ICI / "objets.csv", sep="|").set_index("sujet_id")
    manquants = set(base.sujets.sujet_id) - set(textes.index)
    assert not manquants, f"objets sans texte dans objets.csv : {sorted(manquants)}"
    objets = fiches_objets(base, sv, res, textes)
    futurs = objets_du_jour(res, sv, lignes_swissvotes(args.sources / "swissvotes_dataset.csv", [6880, 6890]))

    figures = ICI / "figures"
    figures.mkdir(exist_ok=True)
    figure_eboulis(res, figures)
    figure_plan_acteurs(res, base, figures)
    figure_plan_acteurs(res, base, figures, 0, 2, "partis_plan13")
    figure_plan_facteurs(res, base, figures)
    figure_cercle(res, objets, figures)
    figure_cercle(res, objets, figures, 0, 2, "cercle13")
    figure_cercle(res, objets, figures, 0, 1, "cercle_facteurs", rot=res["rot3"]["charges"])
    figure_cartes(res, base, args.contours, figures)

    sortie = {
        "meta": {
            "calcule_le": date.today().isoformat(),
            "base": args.base.name,
            "communes": int(base.X.shape[0]),
            "communes_suisses": int((base.communes.ofs < 9000).sum()),
            "objets": int(base.X.shape[1]),
            "premier": base.sujets.date.min(), "dernier": base.sujets.date.max(),
            "reproduction": res["reproduction"], "ecart_max": res["ecart"],
            "sans_force_partis": res["sans_force"],
        },
        "variance": res["variance10"].tolist(),
        "angle_rotation": res["angle"],
        "axes": res["axes"],
        "facteurs": res["facteurs"],
        "acteurs": {a: {"libelle": ACTEURS[a][0], "camp": CAMP[a],
                        "position": res["positions"].loc[a].tolist(),
                        "position_rot": res["rot3"]["acteurs"].loc[a].tolist(),
                        "alignement": res["alignement"][a]["axes"],
                        "n": res["alignement"][a]["n"]} for a in ACTEURS},
        "r2_objets": res["r2_objets"], "r2_objets_rot": res["r2_objets_rot"],
        "r2_communes": res["r2_communes"], "r2_communes_rot": res["r2_communes_rot"],
        "motifs": res["tab_motifs"],
        "suivi": res["suivi"], "force_partis": res["corr_force"],
        "villes": res["villes"],
        "robustesse": {**res["robustesse"],
                       "ajout": (stabilite_ajout(base, lire_base(args.base_avant))
                                 if args.base_avant.exists() else None)},
        "objets": objets,
        "futurs": futurs,
    }
    (ICI / "resultats.json").write_text(json.dumps(sortie, ensure_ascii=False, indent=1, default=_json))
    print(f"{len(objets)} objets, {base.X.shape[0]} communes → {ICI / 'resultats.json'}")


if __name__ == "__main__":
    main()
