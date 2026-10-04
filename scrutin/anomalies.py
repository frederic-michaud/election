"""Erreurs de saisie communales, selon la méthode de doc/anomalies.md.

Deux mesures par commune. Le **vote** : pour chaque objet, la part de oui
des communes dépouillées est ajustée sur leur profil ACP, et l'écart de la
commune se compte en σ. Les **bulletins** : l'écart entre ses nombres de
bulletins d'un objet à l'autre, comparé à ce qu'elle fait d'habitude. On
cherche ensuite la correction simple qui ramène le mieux les deux.

Orange : un écart sur une mesure. Rouge : un très gros écart sur une mesure,
ou un écart sur les deux — y compris une correction qui efface l'écart de vote.
"""

import json
from itertools import combinations

import numpy as np
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from pca.models import NB_AXES, PCAResult
from scrutin.models import (
    Anomalie,
    Commune,
    ResultatCommunalEnCours,
    ResultatCommunalHistorique,
    SujetVote,
)

SEUIL_COMMUNES = 200
NB_VOISINES = 8
# Voix au-delà desquelles l'aléa binomial ne masque plus la dispersion propre à l'objet.
GRANDES = 500
# Au-dessus de l'un des deux, on cherche une correction.
EXAMEN = {"chi2": 10, "bulletins": 5}
# L'écart de bulletins d'une commune varie autour de son habitude d'environ
# 0,35 % de ses bulletins, de 200 à 15 000 bulletins (historique 2014-2026).
KAPPA = 0.0035
MIN_BULLETINS = 10   # en dessous, un écart de bulletins ne compte pas
# chi2, z : écart de vote (χ² sur les objets, plus grand |z|).
# bulletins : écart de bulletins, en σ de l'habitude de la commune.
# explique : χ² de vote après correction, sous lequel elle explique tout.
# avant, apres : |z| qu'une correction doit faire passer de l'un à l'autre.
# gros_z, gros_bulletins : un écart qui suffit seul au rouge.
# On entre avec ENTREE, on ne retombe qu'en passant sous SORTIE : une commune
# ne clignote pas d'un tour à l'autre parce que l'ajustement a bougé.
ENTREE = {"chi2": 20, "z": 5, "bulletins": 8, "explique": 6, "avant": 3, "apres": 1.5,
          "gros_z": 10, "gros_bulletins": 20}
SORTIE = {"chi2": 14, "z": 4, "bulletins": 6, "explique": 9, "avant": 2.5, "apres": 2,
          "gros_z": 8, "gros_bulletins": 15}
CONTOURS = "carte/static/carte/communes.geojson"


class Ajustement:
    """Part de oui prédite et dispersion de chaque objet.

    ``profils`` : communes × axes ; ``oui``, ``non`` : communes × objets.
    """

    def __init__(self, profils, oui, non):
        exprimes = oui + non
        part = oui / exprimes
        design = np.hstack([profils, np.ones((len(profils), 1))])
        self.predit = np.empty_like(part)
        self.tau = np.empty(part.shape[1])
        for i in range(part.shape[1]):
            racine = np.sqrt(exprimes[:, i])
            beta = np.linalg.lstsq(design * racine[:, None], part[:, i] * racine, rcond=None)[0]
            p = np.clip(design @ beta, 0.01, 0.99)
            grandes = exprimes[:, i] >= GRANDES
            if grandes.sum() < 30:  # le matin, les petites communes d'abord
                grandes[:] = True
            binomial = p * (1 - p) / exprimes[:, i]
            self.tau[i] = np.sqrt(max(np.var((part[:, i] - p)[grandes])
                                      - np.mean(binomial[grandes]), 0))
            self.predit[:, i] = p

    def z(self, j, oui, non):
        """Écart en σ de la commune ``j`` sur chaque objet."""
        exprimes = oui + non
        p = self.predit[j]
        return (oui / exprimes - p) / np.sqrt(self.tau ** 2 + p * (1 - p) / exprimes)



def ecart_bulletins(bulletins, habituel):
    """Écart de bulletins entre objets, en σ de ce que la commune fait d'habitude.

    ``habituel`` : son écart habituel, en part de ses bulletins. L'aléa mêle un
    comptage (√) et une part proportionnelle (``KAPPA``) : une grande commune
    est jugée plus sévèrement en %, une petite plus sévèrement en bulletins.
    """
    if len(bulletins) < 2:
        return 0.0
    ecart, total = bulletins.max() - bulletins.min(), bulletins.max()
    if ecart < MIN_BULLETINS:
        return 0.0
    attendu = habituel * total
    return float((ecart - attendu) / np.sqrt(attendu + 1 + (KAPPA * total) ** 2))


def habitudes_bulletins():
    """{commune: écart habituel de bulletins} : la médiane, sur les scrutins
    passés à plusieurs objets, de l'écart rapporté au nombre de bulletins. La
    médiane ignore une erreur passée isolée."""
    par_date = {}
    for commune, date, bulletins in ResultatCommunalHistorique.objects.values_list(
            'commune_id', 'sujet_vote__date', 'bulletins_rentres'):
        par_date.setdefault((commune, date), []).append(bulletins)
    ecarts = {}
    for (commune, _), valeurs in par_date.items():
        if len(valeurs) > 1 and max(valeurs) > 0:
            ecarts.setdefault(commune, []).append((max(valeurs) - min(valeurs)) / max(valeurs))
    return {c: float(np.median(e)) for c, e in ecarts.items() if len(e) >= 5}


def fautes_de_frappe(nombre):
    """Les nombres à une faute de frappe : un chiffre changé, ajouté ou retiré en tête."""
    saisi = str(nombre)
    essais = {saisi[:pos] + c + saisi[pos + 1:] for pos in range(len(saisi)) for c in "0123456789"}
    essais |= {c + saisi for c in "123456789"}
    if len(saisi) > 1:
        essais.add(saisi[1:])
    essais.discard(saisi)
    return sorted({int(e) for e in essais})


def corrections(oui, non, bulletins):
    """(correction, oui, non, bulletins) pour chaque correction simple."""
    for i in range(len(oui)):
        o, n = oui.copy(), non.copy()
        o[i], n[i] = non[i], oui[i]
        yield {"type": "inversion", "objets": [i]}, o, n, bulletins
    for i, k in combinations(range(len(oui)), 2):
        ordre = list(range(len(oui)))
        ordre[i], ordre[k] = k, i
        yield {"type": "echange", "objets": [i, k]}, oui[ordre], non[ordre], bulletins[ordre]
    for i in range(len(oui)):
        for champ, valeurs in (("oui", oui), ("non", non)):
            saisi = int(valeurs[i])
            for vrai in fautes_de_frappe(saisi):
                o, n, b = oui.copy(), non.copy(), bulletins.copy()
                (o if champ == "oui" else n)[i] = vrai
                if o[i] + n[i] <= 0:
                    continue
                # Les bulletins du fichier comptent la faute : on la retire aussi.
                b[i] += vrai - saisi
                yield ({"type": "chiffre", "objets": [i], "champ": champ,
                        "saisi": saisi, "corrige": vrai}, o, n, b)


def mesurer(modele, j, oui, non, bulletins, habituel):
    """Les deux écarts de la commune ``j``, avant et après la meilleure correction."""
    def ecarts(o, n, b):
        z = modele.z(j, o, n)
        return float(np.sum(z ** 2)), float(np.abs(z).max()), ecart_bulletins(b, habituel)

    chi2, z, bul = ecarts(oui, non, bulletins)
    mesure = {"chi2": chi2, "z": z, "bulletins": bul, "correction": None,
              "chi2_corrige": None, "z_corrige": None, "bulletins_corrige": None}
    if chi2 > EXAMEN["chi2"] or bul > EXAMEN["bulletins"]:
        essais = ((ecarts(o, n, b), c) for c, o, n, b in corrections(oui, non, bulletins))
        (chi2_c, z_c, bul_c), correction = min(
            essais, key=lambda essai: essai[0][0] + max(essai[0][2], 0) ** 2)
        mesure.update(correction=correction, chi2_corrige=chi2_c, z_corrige=z_c,
                      bulletins_corrige=bul_c)
    return mesure


def motifs(m, s):
    """Ce qui cloche, selon les seuils ``s`` : "vote", "bulletins", et
    "correction" si une correction simple explique l'écart de vote."""
    trouves = []
    if m["chi2"] > s["chi2"] or m["z"] > s["z"]:
        trouves.append("vote")
    if m["bulletins"] > s["bulletins"]:
        trouves.append("bulletins")
    if m["correction"] is not None and (
            ("vote" in trouves and m["chi2_corrige"] < s["explique"])
            or (m["z"] >= s["avant"] and m["z_corrige"] <= s["apres"])):
        trouves.append("correction")
    return trouves


def classer(m, s):
    """Rouge : un très gros écart sur une mesure, ou un écart sur les deux (la
    correction qui efface l'écart de vote compte pour une). Orange : un écart
    sur une mesure."""
    trouves = motifs(m, s)
    if m["z"] > s["gros_z"] or m["bulletins"] > s["gros_bulletins"] or len(trouves) >= 2:
        return "rouge"
    if "vote" in trouves or "bulletins" in trouves:
        return "orange"
    return "vert"


def niveau(m, precedent="vert"):
    """Niveau avec hystérésis : on garde le niveau précédent tant que les seuils
    de sortie le justifient encore."""
    rang = Anomalie.NIVEAUX.index
    strict = rang(classer(m, ENTREE))
    souple = rang(classer(m, SORTIE))
    return Anomalie.NIVEAUX[max(strict, min(rang(precedent), souple))]


def centres():
    """{numéro OFS: [lon, lat]} : moyenne des sommets extérieurs de la commune."""
    with open(settings.BASE_DIR / CONTOURS) as fichier:
        contours = json.load(fichier)
    resultat = {}
    for commune in contours["features"]:
        geometrie = commune["geometry"]
        polygones = (geometrie["coordinates"] if geometrie["type"] == "MultiPolygon"
                     else [geometrie["coordinates"]])
        sommets = np.concatenate([polygone[0] for polygone in polygones])
        resultat[commune["properties"]["vogeId"]] = [round(float(v), 5) for v in sommets.mean(0)]
    return resultat


def voisines(points, k=NB_VOISINES):
    """Indices des ``k`` plus proches de chaque point ([lon, lat], ou None)."""
    xy = np.array([p if p is not None else [np.nan, np.nan] for p in points], float)
    xy[:, 0] *= np.cos(np.radians(46.8))
    resultat = []
    for j in range(len(xy)):
        if np.isnan(xy[j, 0]):
            resultat.append([])
            continue
        distance = np.hypot(*(xy - xy[j]).T)
        distance[j] = np.inf
        distance[np.isnan(distance)] = np.inf
        resultat.append([int(i) for i in np.argsort(distance)[:k]])
    return resultat


def ecarts_historiques(communes, profils):
    """{commune: [{"date", "nom", "z"}]} : l'écart de chaque commune demandée
    aux objets passés, mesuré comme le jour J. Dit si elle est coutumière du fait."""
    par_sujet = {}
    for commune, sujet, oui, non in ResultatCommunalHistorique.objects.filter(
            commune_id__in=profils).values_list('commune_id', 'sujet_vote_id', 'nombre_oui', 'nombre_non'):
        if oui + non > 0:
            par_sujet.setdefault(sujet, []).append((commune, oui, non))
    resultat = {c: [] for c in communes}
    for sujet in SujetVote.objects.filter(id__in=par_sujet).order_by('date', 'sujet_id'):
        lignes = par_sujet[sujet.id]
        rang = {c: j for j, (c, _, _) in enumerate(lignes)}
        oui = np.array([[o] for _, o, _ in lignes], float)
        non = np.array([[n] for _, _, n in lignes], float)
        modele = Ajustement(np.array([profils[c] for c, _, _ in lignes]), oui, non)
        for c in communes:
            if c in rang:
                j = rang[c]
                z = modele.z(j, oui[j], non[j])[0]
                resultat[c].append({"date": sujet.date.isoformat(), "nom": sujet.nom,
                                    "z": round(float(z), 2)})
    return resultat


def _chiffres(objets):
    return [(o["oui"], o["non"], o["bulletins"]) for o in objets]


def detecter():
    """Recalcule les anomalies du dernier scrutin. Renvoie {niveau: nombre de
    communes}, vide sous ``SEUIL_COMMUNES`` communes dépouillées."""
    jour = SujetVote.objects.latest('date').date
    sujets = list(SujetVote.objects.filter(date=jour).order_by('sujet_id').values_list('id', flat=True))
    profils = {r.commune_id: r.get_component(NB_AXES) for r in PCAResult.objects.all()}

    lignes = {}
    for commune, sujet, oui, non, bulletins in ResultatCommunalEnCours.objects.filter(
            sujet_vote_id__in=sujets, comptabilise=True).values_list(
            'commune_id', 'sujet_vote_id', 'nombre_oui', 'nombre_non', 'bulletins_rentres'):
        lignes.setdefault(commune, {})[sujet] = (oui, non, bulletins if bulletins is not None else oui + non)
    ids = [c for c, r in lignes.items()
           if c in profils and len(r) == len(sujets) and all(o + n > 0 for o, n, _ in r.values())]
    if len(ids) < SEUIL_COMMUNES:
        return {}

    oui, non, bulletins = (np.array([[lignes[c][s][k] for s in sujets] for c in ids], float)
                           for k in range(3))
    modele = Ajustement(np.array([profils[c] for c in ids]), oui, non)
    habitudes = habitudes_bulletins()
    # Une commune sans passé à plusieurs objets : l'habitude médiane du pays.
    habitude_nationale = float(np.median(list(habitudes.values()))) if habitudes else 0.0
    z = np.array([modele.z(j, oui[j], non[j]) for j in range(len(ids))])
    numeros = dict(Commune.objects.filter(id__in=ids).values_list('id', 'numero_ofs'))
    tous_centres = centres()
    points = [tous_centres.get(numeros[c]) for c in ids]
    proches = voisines(points)

    anciennes = {a.commune_id: a for a in Anomalie.objects.filter(date=jour)}
    maintenant = timezone.now()
    nouvelles, modifiees, sans_historique = [], [], []
    for j, c in enumerate(ids):
        habituel = habitudes.get(c, habitude_nationale)
        m = mesurer(modele, j, oui[j], non[j], bulletins[j], habituel)
        objets = [{
            "oui": int(oui[j, i]), "non": int(non[j, i]), "bulletins": int(bulletins[j, i]),
            "predit": round(float(modele.predit[j, i]), 4),
            "z": round(float(z[j, i]), 2),
            "z_voisines": round(float(np.median(z[proches[j], i])), 2) if proches[j] else None,
        } for i in range(len(sujets))]

        ancienne = anciennes.get(c)
        # Des chiffres corrigés dans le fichier fédéral : on repart de zéro.
        precedent = (ancienne.niveau if ancienne and _chiffres(ancienne.objets) == _chiffres(objets)
                     else "vert")
        niv = niveau(m, precedent)
        signalee_depuis = None
        if niv != "vert":
            signalee_depuis = (ancienne.signalee_depuis if ancienne and ancienne.niveau != "vert"
                               else maintenant)
        anomalie = ancienne or Anomalie(date=jour, commune_id=c)
        anomalie.niveau = niv
        anomalie.motifs = motifs(m, SORTIE)
        anomalie.chi2 = round(m["chi2"], 2)
        anomalie.chi2_corrige = None if m["chi2_corrige"] is None else round(m["chi2_corrige"], 2)
        anomalie.correction = m["correction"]
        anomalie.ecart_bulletins = round(m["bulletins"], 2)
        anomalie.bulletins_habituel = round(habituel, 4)
        anomalie.objets = objets
        anomalie.voisines = [numeros[ids[k]] for k in proches[j]]
        anomalie.centre = points[j]
        anomalie.signalee_depuis = signalee_depuis
        anomalie.mise_a_jour = maintenant
        (modifiees if ancienne else nouvelles).append(anomalie)
        if niv != "vert" and anomalie.historique is None:
            sans_historique.append(anomalie)

    # Coûteux (tout l'historique) : seulement pour les communes signalées qui ne l'ont pas.
    if sans_historique:
        historiques = ecarts_historiques([a.commune_id for a in sans_historique], profils)
        for anomalie in sans_historique:
            anomalie.historique = historiques[anomalie.commune_id]

    champs = ["niveau", "motifs", "chi2", "chi2_corrige", "correction", "ecart_bulletins",
              "bulletins_habituel", "objets", "voisines", "centre",
              "historique", "signalee_depuis", "mise_a_jour"]
    with transaction.atomic():
        Anomalie.objects.bulk_create(nouvelles, batch_size=500)
        Anomalie.objects.bulk_update(modifiees, champs, batch_size=500)
        # Une commune qui n'est plus dépouillée ; sa note, s'il y en a une, reste.
        Anomalie.objects.filter(date=jour, note="").exclude(commune_id__in=ids).delete()

    compte = {n: 0 for n in Anomalie.NIVEAUX}
    for anomalie in nouvelles + modifiees:
        compte[anomalie.niveau] += 1
    return compte
