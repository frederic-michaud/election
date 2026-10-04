"""Détecteur d'erreurs de saisie : ``scrutin/anomalies.py`` et sa page.

Sur des données synthétiques, une erreur semée doit être retrouvée avec sa
correction exacte ; un écart sans correction simple reste orange.
"""

import numpy as np
import pytest

from scrutin.anomalies import (
    ENTREE,
    SEUIL_COMMUNES,
    Ajustement,
    classer,
    detecter,
    ecart_bulletins,
    fautes_de_frappe,
    mesurer,
    niveau,
)
from scrutin.donnees import construire_vue_anomalies
from scrutin.models import Anomalie, ResultatCommunalEnCours

NB_COMMUNES, NB_OBJETS = 800, 3


@pytest.fixture
def scrutin():
    """Des communes qui votent selon leur profil, avec un peu de dispersion."""
    alea = np.random.default_rng(1)
    profils = alea.normal(size=(NB_COMMUNES, 2))
    pentes = np.array([[0.08, -0.05, 0.02], [0.03, 0.06, -0.07]])
    vrai = np.clip(np.array([0.55, 0.35, 0.62]) + profils @ pentes
                   + alea.normal(0, 0.02, (NB_COMMUNES, NB_OBJETS)), 0.05, 0.95)
    votants = alea.integers(80, 3000, NB_COMMUNES)
    blancs = alea.integers(0, 5, (NB_COMMUNES, NB_OBJETS))
    exprimes = votants[:, None] - blancs
    oui = alea.binomial(exprimes, vrai).astype(float)
    return profils, oui, exprimes - oui, np.repeat(votants[:, None], NB_OBJETS, 1).astype(float)


def juger(profils, oui, non, bulletins, j, habituel=0.01):
    modele = Ajustement(profils, oui, non)
    m = mesurer(modele, j, oui[j], non[j], bulletins[j], habituel)
    return m, classer(m, ENTREE)


def commune_tranchee(oui, non, objet=0):
    """Une commune dont la part de oui est loin de 50 % : l'inversion se voit."""
    part = oui[:, objet] / (oui[:, objet] + non[:, objet])
    return int(np.argmax((np.abs(part - 0.5) > 0.15) & (oui[:, objet] + non[:, objet] > 300)))


def test_fautes_de_frappe():
    essais = fautes_de_frappe(175)
    assert {275, 165, 178, 75, 1175} <= set(essais)
    assert 175 not in essais
    assert fautes_de_frappe(7) == [0, 1, 2, 3, 4, 5, 6, 8, 9, 17, 27, 37, 47, 57, 67, 77, 87, 97]


def test_oui_et_non_inverses(scrutin):
    profils, oui, non, bulletins = scrutin
    j = commune_tranchee(oui, non)
    oui[j, 0], non[j, 0] = non[j, 0], oui[j, 0]

    m, couleur = juger(profils, oui, non, bulletins, j)

    assert m["correction"] == {"type": "inversion", "objets": [0]}
    assert m["chi2"] > 20 and m["chi2_corrige"] < 6
    assert couleur == "rouge"


def test_objets_intervertis(scrutin):
    profils, oui, non, bulletins = scrutin
    part = oui / (oui + non)
    j = int(np.argmax(np.abs(part[:, 0] - part[:, 1]) * (oui[:, 0] > 300)))
    for tableau in (oui, non, bulletins):
        tableau[j, [0, 1]] = tableau[j, [1, 0]]

    m, couleur = juger(profils, oui, non, bulletins, j)

    assert m["correction"] == {"type": "echange", "objets": [0, 1]}
    assert couleur == "rouge"


def test_un_chiffre_mal_saisi_se_trahit_par_les_bulletins(scrutin):
    """Le cas de Wolfhalden : 275 oui saisis pour 175, et le total de bulletins
    de l'objet gonflé d'autant."""
    profils, oui, non, bulletins = scrutin
    j = int(np.argmax((oui[:, 2] >= 100) & (oui[:, 2] + non[:, 2] < 800)))
    saisi, vrai = oui[j, 2] + 100, oui[j, 2]
    oui[j, 2] = saisi
    bulletins[j, 2] += 100

    m, couleur = juger(profils, oui, non, bulletins, j)

    assert m["correction"] == {"type": "chiffre", "objets": [2], "champ": "oui",
                               "saisi": int(saisi), "corrige": int(vrai)}
    assert m["bulletins_corrige"] == 0
    assert couleur == "rouge"


def test_un_ecart_sans_correction_simple_reste_orange(scrutin):
    profils, oui, non, bulletins = scrutin
    j = commune_tranchee(oui, non, objet=1)
    exprimes = oui[j, 1] + non[j, 1]
    oui[j, 1] = min(exprimes, round(oui[j, 1] + 0.2 * exprimes))
    non[j, 1] = exprimes - oui[j, 1]

    m, couleur = juger(profils, oui, non, bulletins, j)

    assert m["chi2_corrige"] > 6
    assert couleur == "orange"


def test_une_commune_ordinaire_reste_verte(scrutin):
    profils, oui, non, bulletins = scrutin
    couleurs = [juger(profils, oui, non, bulletins, j)[1] for j in range(NB_COMMUNES)]
    assert couleurs.count("vert") >= NB_COMMUNES - 2


def test_l_ecart_de_bulletins_tient_compte_de_la_taille():
    """Petite commune : quelques bulletins ne comptent pas. Grande commune :
    quelques pour cent font des centaines de bulletins."""
    assert ecart_bulletins(np.array([200., 191.]), 0.0) == 0          # moins de 10
    assert ecart_bulletins(np.array([200., 188.]), 0.01) < 8          # 6 %, mais 12 bulletins
    assert ecart_bulletins(np.array([5612., 5367.]), 0.01) > 8        # Allschwil, 4,4 %
    assert ecart_bulletins(np.array([5612., 5560.]), 0.01) < 1        # son habitude
    assert ecart_bulletins(np.array([5612.]), 0.01) == 0              # un seul objet


def mesure(**valeurs):
    m = {"chi2": 1, "z": 1, "bulletins": 0, "correction": None,
         "chi2_corrige": None, "z_corrige": None, "bulletins_corrige": None}
    m.update(valeurs)
    return m


CORRECTION = {"type": "chiffre", "objets": [1], "champ": "oui", "saisi": 275, "corrige": 175}


def test_rouge_un_gros_ecart_ou_deux_ecarts():
    # Une mesure : orange.
    assert classer(mesure(bulletins=12), ENTREE) == "orange"
    assert classer(mesure(chi2=30, z=5.4), ENTREE) == "orange"
    # Une très grosse : rouge.
    assert classer(mesure(bulletins=25), ENTREE) == "rouge"
    assert classer(mesure(chi2=130, z=11), ENTREE) == "rouge"
    # Wolfhalden : des bulletins anormaux, et une correction qui fait passer
    # le vote de 3,3 σ à presque rien.
    wolfhalden = mesure(chi2=10.9, z=3.3, bulletins=12, correction=CORRECTION,
                        chi2_corrige=0.9, z_corrige=0.6, bulletins_corrige=0)
    assert classer(wolfhalden, ENTREE) == "rouge"
    # La même correction qui n'améliore pas le vote : orange.
    assert classer({**wolfhalden, "z_corrige": 2.5, "chi2_corrige": 7}, ENTREE) == "orange"
    # Un gros écart de vote qu'une correction efface : rouge (Verzasca).
    assert classer(mesure(chi2=180, z=13.4, correction=CORRECTION, chi2_corrige=2.8,
                          z_corrige=1.2), ENTREE) == "rouge"


def test_hysteresis():
    # Assez pour rester orange, pas pour le devenir.
    assert niveau(mesure(bulletins=7), precedent="vert") == "vert"
    assert niveau(mesure(bulletins=7), precedent="orange") == "orange"
    # Une commune qui n'a plus rien d'anormal redevient verte.
    assert niveau(mesure(), precedent="rouge") == "vert"
    # Le niveau peut toujours monter.
    assert niveau(mesure(bulletins=25), precedent="orange") == "rouge"


# ── Sur la base de démonstration, où peupler_demo sème quatre erreurs ──


@pytest.mark.lent
@pytest.mark.django_db
def test_la_demo_montre_les_trois_fautes_semees(base_demo):
    rouges = {a.correction["type"] for a in Anomalie.objects.filter(niveau="rouge")}
    assert {"inversion", "echange", "chiffre"} <= rouges
    assert Anomalie.objects.filter(niveau="orange").exists()


@pytest.mark.lent
@pytest.mark.django_db
def test_la_note_survit_au_tour_suivant_et_la_correction_efface_le_rouge(base_demo):
    anomalie = Anomalie.objects.filter(niveau="rouge", correction__type="chiffre").first()
    anomalie.note = "La commune a confirmé."
    anomalie.save()
    # Le fichier fédéral est corrigé.
    correction = anomalie.correction
    ligne = ResultatCommunalEnCours.objects.filter(commune=anomalie.commune, comptabilise=True) \
        .order_by("sujet_vote__sujet_id")[correction["objets"][0]]
    ligne.nombre_oui = correction["corrige"]
    ligne.bulletins_rentres -= correction["saisi"] - correction["corrige"]
    ligne.save()

    detecter()

    anomalie.refresh_from_db()
    assert anomalie.note == "La commune a confirmé."
    assert anomalie.niveau == "vert"
    assert anomalie.signalee_depuis is None


@pytest.mark.lent
@pytest.mark.django_db
def test_sous_le_seuil_rien_n_est_juge(base_demo):
    Anomalie.objects.all().delete()
    garder = list(ResultatCommunalEnCours.objects.filter(comptabilise=True)
                  .values_list("commune_id", flat=True).distinct()[:SEUIL_COMMUNES - 1])
    ResultatCommunalEnCours.objects.exclude(commune_id__in=garder).update(comptabilise=False)

    assert detecter() == {}
    vue = construire_vue_anomalies()
    assert vue["communes"] == [] and vue["depouillees"] == SEUIL_COMMUNES - 1


@pytest.mark.lent
@pytest.mark.django_db
def test_la_page_des_anomalies(base_demo, client):
    vue = construire_vue_anomalies()
    assert set(vue) == {"date", "seuil", "depouillees", "mise_a_jour", "objets", "communes"}
    niveaux = [c["niveau"] for c in vue["communes"]]
    assert niveaux == sorted(niveaux, key=["rouge", "orange", "vert"].index)

    reponse = client.get("/anomalies")
    assert reponse.status_code == 200
    contenu = reponse.content.decode()
    assert "Résultats atypiques" in contenu
    assert "saisis pour" in contenu and "intervertis" in contenu and "inversés" in contenu
