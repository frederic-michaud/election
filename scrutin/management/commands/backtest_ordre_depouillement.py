"""Backtest de l'extrapolation face à l'ordre d'arrivée des communes.

Rejoue des scrutins passés commune par commune, sous trois ordres d'arrivée
(deux adversariaux, un réaliste), et trace le %oui projeté en fonction de
l'avance.

Lecture seule : la base est ouverte en `mode=ro` via sqlite3, jamais par l'ORM.
Ni PCAResult ni ResultatCommunalEnCours ne sont touchés — l'ACP de chaque date
cible est recalculée en mémoire sur les seuls objets antérieurs.
"""

import csv
import gzip
import os
import sqlite3
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
from django.core.management.base import BaseCommand, CommandError

NB_COMPOSANTES = 6
SEUIL_COMMUNES = 7  # garde-fou de get_extrapolation
# Les deux « adversarial_* » trient sur le %oui de l'objet : ils sélectionnent
# sur le résidu, que l'historique ne peut pas prévoir. Ce sont des bornes
# d'oracle, pas des ordres qu'un processus réel puisse produire. Les deux
# « profil_* » trient sur la 1re composante ACP — un ordre tout aussi hostile,
# mais entièrement déterminé par l'historique, donc physiquement atteignable.
COULEURS = {"adversarial_bas": "tab:red",
            "adversarial_haut": "tab:orange",
            "profil_bas": "tab:purple",
            "profil_haut": "tab:green",
            "realiste": "tab:blue"}
# Loi d'arrivée calibrée sur les kommunale_resultate_* du BFS (ZH/AG/GR/SZ/ZG),
# 181 communes x 18 dates : retard = 80*log10(electeurs) + N(0, 46 min).
RETARD_PENTE = 80.0
RETARD_SIGMA = 46.0


# --------------------------------------------------------------------------
# Chargement (lecture seule)
# --------------------------------------------------------------------------

def charger(chemin):
    """Historique complet en tableaux denses commune x objet (NaN si absent)."""
    if not Path(chemin).exists():
        raise CommandError(f"Base introuvable : {chemin}")
    conn = sqlite3.connect(f"file:{chemin}?mode=ro&immutable=1", uri=True)
    sujets = conn.execute(
        "select id, sujet_id, date, nom from scrutin_sujetvote order by date, sujet_id"
    ).fetchall()
    communes = conn.execute("select id, nom from scrutin_commune order by id").fetchall()
    idx_sujet = {s[0]: j for j, s in enumerate(sujets)}
    idx_commune = {c[0]: i for i, c in enumerate(communes)}

    forme = (len(communes), len(sujets))
    oui = np.full(forme, np.nan)
    non = np.full(forme, np.nan)
    elec = np.full(forme, np.nan)
    bul = np.full(forme, np.nan)
    for cid, sid, o, n, e, b in conn.execute(
        "select commune_id, sujet_vote_id, nombre_oui, nombre_non, "
        "electeurs_inscrits, bulletins_rentres from scrutin_resultatcommunalhistorique"
    ):
        i, j = idx_commune[cid], idx_sujet[sid]
        oui[i, j], non[i, j], elec[i, j], bul[i, j] = o, n, e, b
    conn.close()
    return sujets, communes, oui, non, elec, bul


def choisir_cibles(sujets, min_anterieurs, par_annee, journal):
    """Une date est éligible si assez d'objets la précèdent strictement.

    On garde ensuite le premier objet (par sujet_id) de chacune des premières
    dates éligibles de chaque année civile.
    """
    dates = sorted({s[2] for s in sujets})
    premier_de_la_date = {}
    for j, s in enumerate(sujets):
        premier_de_la_date.setdefault(s[2], j)
    par_an = defaultdict(list)
    for d in dates:
        par_an[d[:4]].append(d)

    cibles = []
    for annee in sorted(par_an):
        eligibles = [(d, sum(1 for s in sujets if s[2] < d)) for d in par_an[annee]]
        eligibles = [(d, n) for d, n in eligibles if n >= min_anterieurs]
        retenues = eligibles[:par_annee]
        if retenues and len(retenues) < par_annee:
            journal(f"  {annee} : {len(retenues)} date(s) éligible(s) sur "
                    f"{len(par_an[annee])} — moins que les {par_annee} demandées")
        for d, nb in retenues:
            cibles.append((premier_de_la_date[d], nb))
    return cibles


# --------------------------------------------------------------------------
# ACP antérieure, en mémoire
# --------------------------------------------------------------------------

def acp_anterieure(oui, non, indices_anterieurs):
    """Reproduit getVotationMatrixWithMetaInfo + PCA(6) sur les objets antérieurs.

    Le critère d'exclusion se recalcule ici : une commune est retenue si elle a
    un résultat pour *tous* les objets antérieurs, pas pour les 103 de la base.
    """
    from sklearn.decomposition import PCA

    sous_oui = oui[:, indices_anterieurs]
    sous_non = non[:, indices_anterieurs]
    valide = ~np.isnan(sous_oui).any(axis=1) & ~np.isnan(sous_non).any(axis=1)
    matrice = sous_oui[valide] / (sous_oui[valide] + sous_non[valide])
    composantes = PCA(n_components=NB_COMPOSANTES).fit_transform(matrice)
    return valide, composantes


# --------------------------------------------------------------------------
# Étape 1 — extrapolation pure, sans ORM
# --------------------------------------------------------------------------

def ajuster(design, cible, poids):
    """Moindres carrés pondérés, solution fermée.

    Delta_fast est quadratique en ses 7 paramètres : le minimum est celui de
    lstsq(sqrt(w)·X, sqrt(w)·y), sans passer par un BFGS.
    """
    racine = np.sqrt(poids)
    beta, *_ = np.linalg.lstsq(design * racine[:, None], cible * racine, rcond=None)
    return beta


def extrapoler(composantes, pourcentage_oui, participation, bulletins, exprimes,
               electeurs_precedents, depouillees):
    """%oui projeté, avance, diagnostic — à partir de tableaux alignés.

    `exprimes` (= nombre_oui + nombre_non) s'ajoute à la signature : le
    dépouillement confirmé se somme en voix, pas en pourcentages.
    """
    if depouillees.sum() < SEUIL_COMMUNES:
        return 0.5, 0.0, {}
    design = np.column_stack([composantes, np.ones(len(composantes))])
    poids = bulletins[depouillees].astype(float)
    beta_oui = ajuster(design[depouillees], pourcentage_oui[depouillees], poids)
    beta_part = ajuster(design[depouillees], participation[depouillees], poids)

    manquantes = ~depouillees
    projete_oui = design[manquantes] @ beta_oui
    projete_part = design[manquantes] @ beta_part
    votants = projete_part * electeurs_precedents[manquantes]
    oui_connu = (pourcentage_oui[depouillees] * exprimes[depouillees]).sum()
    exprimes_connus = exprimes[depouillees].sum()
    oui_final = oui_connu + (projete_oui * votants).sum()
    total_final = exprimes_connus + votants.sum()

    gram = (design[depouillees] * poids[:, None]).T @ design[depouillees]
    inverse = np.linalg.inv(gram)
    leviers = np.einsum("ni,ij,nj->n", design[manquantes], inverse, design[manquantes])
    diagnostic = {"cond": np.linalg.cond(gram),
                  "levier_max": leviers.max() if leviers.size else np.nan,
                  "poids_total": poids.sum()}
    return oui_final / total_final, exprimes_connus / total_final, diagnostic


# --------------------------------------------------------------------------
# Étapes 2-3 — balayage vectorisé par mises à jour de rang 1
# --------------------------------------------------------------------------

def balayer(composantes, pourcentage_oui, participation, bulletins, exprimes,
            oui_absolus, electeurs_precedents, ordre, effectifs):
    """Toutes les grandeurs aux `effectifs` demandés, en un seul passage.

    XᵀWX et XᵀWy sont des sommes de termes wᵢ·xᵢxᵢᵀ : un cumsum sur les communes
    rangées dans l'ordre d'arrivée les donne tous d'un coup, et il ne reste que
    G résolutions 7x7.
    """
    nb = len(ordre)
    design = np.column_stack([composantes, np.ones(nb)])[ordre]
    poids = bulletins[ordre].astype(float)
    pondere = design * poids[:, None]

    gram = np.cumsum(np.einsum("ni,nj->nij", pondere, design), axis=0)
    second_oui = np.cumsum(pondere * pourcentage_oui[ordre][:, None], axis=0)
    second_part = np.cumsum(pondere * participation[ordre][:, None], axis=0)
    cumul_oui = np.cumsum(oui_absolus[ordre])
    cumul_exprimes = np.cumsum(exprimes[ordre])

    pos = effectifs - 1
    grammes = gram[pos]
    try:
        beta_oui = np.linalg.solve(grammes, second_oui[pos][..., None])[..., 0]
        beta_part = np.linalg.solve(grammes, second_part[pos][..., None])[..., 0]
        inverses = np.linalg.inv(grammes)
    except np.linalg.LinAlgError:
        inverses = np.linalg.pinv(grammes)
        beta_oui = np.einsum("gij,gj->gi", inverses, second_oui[pos])
        beta_part = np.einsum("gij,gj->gi", inverses, second_part[pos])

    projete_oui = beta_oui @ design.T           # (G, nb)
    projete_part = beta_part @ design.T
    votants = projete_part * electeurs_precedents[ordre][None, :]
    apport_oui = projete_oui * votants

    colonnes = np.arange(nb)
    manquante = colonnes[None, :] >= effectifs[:, None]
    suffixe_oui = np.where(manquante, apport_oui, 0.0).sum(axis=1)
    suffixe_tot = np.where(manquante, votants, 0.0).sum(axis=1)

    oui_final = cumul_oui[pos] + suffixe_oui
    total_final = cumul_exprimes[pos] + suffixe_tot
    leviers = np.einsum("gij,ni,nj->gn", inverses, design, design)
    levier_max = np.where(manquante, leviers, -np.inf).max(axis=1)
    levier_max[effectifs >= nb] = np.nan

    return {"avance": cumul_exprimes[pos] / cumul_exprimes[-1],
            "avance_affichee": cumul_exprimes[pos] / total_final,
            "oui_projete": oui_final / total_final,
            "oui_depouille": cumul_oui[pos] / cumul_exprimes[pos],
            "cond": np.linalg.cond(grammes),
            "levier_max": levier_max,
            "nb_depouillees": effectifs.astype(float),
            "poids_total": np.cumsum(poids)[pos]}


def ordres(scenario, pourcentage_oui, composantes, electeurs, rng):
    if scenario == "adversarial_bas":
        return np.argsort(pourcentage_oui, kind="stable")
    if scenario == "adversarial_haut":
        return np.argsort(-pourcentage_oui, kind="stable")
    if scenario == "profil_bas":
        return np.argsort(composantes[:, 0], kind="stable")
    if scenario == "profil_haut":
        return np.argsort(-composantes[:, 0], kind="stable")
    retard = RETARD_PENTE * np.log10(np.maximum(electeurs, 1.0))
    retard = retard + rng.normal(0.0, RETARD_SIGMA, size=len(electeurs))
    return np.argsort(retard, kind="stable")


# --------------------------------------------------------------------------
# Commande
# --------------------------------------------------------------------------

class Command(BaseCommand):
    help = ("Backtest de l'extrapolation sous trois ordres de dépouillement. "
            "Lecture seule, rien n'est écrit en base.")

    def add_arguments(self, parser):
        parser.add_argument("--base", default="var/backtest/snapshot.sqlite3",
                            help="Base sqlite ouverte en lecture seule")
        parser.add_argument("--min-objets-anterieurs", type=int, default=20)
        parser.add_argument("--objets-par-annee", type=int, default=4)
        parser.add_argument("--tirages", type=int, default=1)
        parser.add_argument("--graine", type=int, default=0)
        parser.add_argument("--grille", type=int, default=200)
        parser.add_argument("--sortie", default="var/backtest")
        parser.add_argument("--cibles", default=None,
                            help="Restreint à ces sujet_id, séparés par des virgules")
        parser.add_argument("--seuil-levier", type=float, default=None,
                            help="Sinon calibré sur le scénario réaliste")
        parser.add_argument("--marge-graphique", type=float, default=10.0,
                            help="Demi-hauteur de l'axe y, en points de %%oui")
        parser.add_argument("--memoire-max-mo", type=int, default=1400)
        parser.add_argument("--test-equivalence", action="store_true",
                            help="Compare lstsq et scipy.optimize.minimize, puis sort")
        parser.add_argument("--chronometre", action="store_true",
                            help="Chronomètre une cible et extrapole le coût, puis sort")
        parser.add_argument("--figure-mecanisme", action="store_true",
                            help="Trace pourquoi le tri sur le %%oui biaise, et pas le tri sur le profil")
        parser.add_argument("--analyse-garde-fou", action="store_true",
                            help="Relit courbes.csv.gz et compare les prédicteurs de fiabilité")

    # ---------------------------------------------------------------- outils

    def journal(self, message):
        self.stdout.write(message)

    def memoire_mo(self):
        with open("/proc/self/statm") as fichier:
            return int(fichier.read().split()[1]) * os.sysconf("SC_PAGE_SIZE") / 2**20

    def garde_memoire(self, limite):
        utilisee = self.memoire_mo()
        if utilisee > limite:
            raise CommandError(f"Mémoire dépassée : {utilisee:.0f} Mo > {limite} Mo")
        return utilisee

    def preparer(self, options):
        sujets, communes, oui, non, elec, bul = charger(options["base"])
        cibles = choisir_cibles(sujets, options["min_objets_anterieurs"],
                                options["objets_par_annee"], self.journal)
        if options["cibles"]:
            voulus = {int(x) for x in options["cibles"].split(",")}
            cibles = [(j, n) for j, n in cibles if sujets[j][1] in voulus]
        return sujets, communes, oui, non, elec, bul, cibles

    def contexte(self, cible, sujets, oui, non, elec, bul, cache):
        """Tout ce qu'il faut pour rejouer un objet : ACP, %oui, participation."""
        indice, _ = cible
        date = sujets[indice][2]
        anterieurs = [j for j, s in enumerate(sujets) if s[2] < date]
        if date not in cache:
            cache.clear()  # une seule ACP en mémoire à la fois
            cache[date] = acp_anterieure(oui, non, anterieurs)
        valide, composantes = cache[date]

        cible_ok = ~np.isnan(oui[:, indice]) & ~np.isnan(non[:, indice]) \
            & (elec[:, indice] > 0) & (bul[:, indice] > 0)
        garde = valide & cible_ok
        # composantes est indexé sur `valide` : on re-sélectionne.
        composantes = composantes[garde[valide]]

        precedent = max(anterieurs, key=lambda j: sujets[j][2])
        exprimes = oui[garde, indice] + non[garde, indice]
        return {
            "date": date, "nom": sujets[indice][3], "sujet_id": sujets[indice][1],
            "nb_objets_acp": len(anterieurs), "composantes": composantes,
            "pourcentage_oui": oui[garde, indice] / exprimes,
            "participation": exprimes / elec[garde, indice],
            "bulletins": bul[garde, indice], "exprimes": exprimes,
            "oui_absolus": oui[garde, indice],
            "electeurs_precedents": elec[garde, precedent],
            "electeurs": elec[garde, indice],
            "vrai_oui": oui[garde, indice].sum() / exprimes.sum(),
            "nb_communes": int(garde.sum()),
            "nb_exclues": int(len(garde) - garde.sum()),
            "part_electeurs_exclus": 1 - elec[garde, indice].sum()
            / np.nansum(elec[:, indice]),
        }

    def effectifs(self, nb, grille):
        """Grille log-espacée en nombre de communes : le fin est aux faibles avances."""
        brut = np.unique(np.round(np.geomspace(SEUIL_COMMUNES, nb, grille)).astype(int))
        return brut[(brut >= SEUIL_COMMUNES) & (brut <= nb)]

    def courbes_objet(self, ctx, options, grille_avance):
        """Une ligne par scénario x tirage, interpolée sur la grille commune."""
        rng = np.random.default_rng(options["graine"] + ctx["sujet_id"])
        effectifs = self.effectifs(ctx["nb_communes"], options["grille"])
        resultats = {}
        for scenario in COULEURS:
            nb_tirages = options["tirages"] if scenario == "realiste" else 1
            empile = {cle: [] for cle in ("oui_projete", "oui_depouille",
                                          "avance_affichee", "cond", "levier_max",
                                          "nb_depouillees")}
            for _ in range(nb_tirages):
                ordre = ordres(scenario, ctx["pourcentage_oui"], ctx["composantes"],
                               ctx["electeurs"], rng)
                brut = balayer(ctx["composantes"], ctx["pourcentage_oui"],
                               ctx["participation"], ctx["bulletins"], ctx["exprimes"],
                               ctx["oui_absolus"], ctx["electeurs_precedents"],
                               ordre, effectifs)
                avance = brut["avance"]
                if np.any(np.diff(avance) <= 0):
                    raise CommandError("avance non monotone : l'interpolation "
                                       "déplacerait des points de la courbe")
                for cle in empile:
                    interpolee = np.interp(grille_avance, avance, brut[cle],
                                           left=np.nan, right=np.nan)
                    interpolee[grille_avance < avance[0]] = np.nan
                    empile[cle].append(interpolee)
            resultats[scenario] = {cle: np.array(v) for cle, v in empile.items()}
        return resultats

    # ------------------------------------------------------------ handle

    def handle(self, *args, **options):
        os.environ.setdefault("OMP_NUM_THREADS", "1")
        sortie = Path(options["sortie"])
        sortie.mkdir(parents=True, exist_ok=True)

        if options["test_equivalence"]:
            return self.test_equivalence(options)
        if options["analyse_garde_fou"]:
            return self.analyse_garde_fou(options)
        if options["figure_mecanisme"]:
            return self.figure_mecanisme(options)

        sujets, communes, oui, non, elec, bul, cibles = self.preparer(options)
        self.journal(f"{len(cibles)} cible(s), base {options['base']}")
        if not cibles:
            raise CommandError("Aucune cible sélectionnée")

        grille_avance = np.geomspace(0.002, 1.0, options["grille"])
        cache, toutes, meta = {}, {}, []
        depart = time.perf_counter()
        for rang, cible in enumerate(cibles, 1):
            debut = time.perf_counter()
            ctx = self.contexte(cible, sujets, oui, non, elec, bul, cache)
            courbes = self.courbes_objet(ctx, options, grille_avance)
            toutes[ctx["sujet_id"]] = courbes
            meta.append(ctx)
            duree = time.perf_counter() - debut
            memoire = self.garde_memoire(options["memoire_max_mo"])
            self.journal(f"  [{rang}/{len(cibles)}] {ctx['date']} sujet {ctx['sujet_id']} "
                         f"— {ctx['nb_communes']} communes, {ctx['nb_objets_acp']} objets ACP, "
                         f"vrai oui {100*ctx['vrai_oui']:.2f}% — {duree:.1f}s, {memoire:.0f} Mo")
            if options["chronometre"]:
                cout = duree * len(cibles)
                self.journal(f"\nCoût extrapolé pour {len(cibles)} cibles x "
                             f"{options['tirages']} tirages : {cout:.0f} s "
                             f"({cout/60:.1f} min), pic mémoire {memoire:.0f} Mo")
                return

        self.journal(f"Balayage terminé en {time.perf_counter()-depart:.0f} s")
        self.ecrire_courbes(sortie, meta, toutes, grille_avance)
        seuil = self.calibrer_levier(meta, toutes, grille_avance, options)
        table = self.synthese(sortie, meta, toutes, grille_avance, seuil, options)
        self.figures(sortie, meta, toutes, grille_avance, options)
        self.resume(table, meta, toutes, grille_avance, seuil)

    # -------------------------------------------------------------- sorties

    def ecrire_courbes(self, sortie, meta, toutes, grille_avance):
        chemin = sortie / "courbes.csv.gz"
        with gzip.open(chemin, "wt", newline="") as fichier:
            plume = csv.writer(fichier)
            plume.writerow(["date", "sujet", "scenario", "tirage", "avance",
                            "oui_projete", "oui_depouille", "avance_affichee",
                            "cond", "levier_max", "nb_depouillees"])
            for ctx in meta:
                for scenario, donnees in toutes[ctx["sujet_id"]].items():
                    for tirage in range(len(donnees["oui_projete"])):
                        for k, avance in enumerate(grille_avance):
                            valeur = donnees["oui_projete"][tirage, k]
                            if np.isnan(valeur):
                                continue
                            plume.writerow([ctx["date"], ctx["sujet_id"], scenario, tirage,
                                            f"{avance:.6f}", f"{valeur:.6f}",
                                            f"{donnees['oui_depouille'][tirage, k]:.6f}",
                                            f"{donnees['avance_affichee'][tirage, k]:.6f}",
                                            f"{donnees['cond'][tirage, k]:.6g}",
                                            f"{donnees['levier_max'][tirage, k]:.6g}",
                                            f"{donnees['nb_depouillees'][tirage, k]:.1f}"])
        self.journal(f"Courbes brutes : {chemin}")

    def calibrer_levier(self, meta, toutes, grille_avance, options):
        """Seuil = levier typique au moment où le réaliste passe sous 1 point."""
        if options["seuil_levier"] is not None:
            return options["seuil_levier"]
        valeurs = []
        for ctx in meta:
            donnees = toutes[ctx["sujet_id"]]["realiste"]
            moyenne = np.nanmean(donnees["oui_projete"], axis=0)
            erreur = np.abs(moyenne - ctx["vrai_oui"]) * 100
            avance = self.avance_sous(grille_avance, erreur, 1.0)
            if np.isnan(avance):
                continue
            levier = np.nanmean(donnees["levier_max"], axis=0)
            valeurs.append(np.interp(avance, grille_avance, levier))
        return float(np.median(valeurs)) if valeurs else np.nan

    @staticmethod
    def avance_sous(grille, erreur, seuil):
        """Avance à partir de laquelle l'erreur reste sous le seuil."""
        valide = ~np.isnan(erreur)
        if not valide.any():
            return np.nan
        depasse = np.where(valide & (erreur >= seuil))[0]
        if len(depasse) == 0:
            return float(grille[valide][0])
        dernier = depasse[-1]
        if dernier + 1 >= len(grille):
            return np.nan
        return float(grille[dernier + 1])

    @staticmethod
    def avance_levier_sous(grille, levier, seuil):
        valide = ~np.isnan(levier)
        if not valide.any() or np.isnan(seuil):
            return np.nan
        depasse = np.where(valide & (levier >= seuil))[0]
        if len(depasse) == 0:
            return float(grille[valide][0])
        if depasse[-1] + 1 >= len(grille):
            return np.nan
        return float(grille[depasse[-1] + 1])

    def synthese(self, sortie, meta, toutes, grille_avance, seuil, options):
        lignes = []
        marge = options["marge_graphique"] / 100
        for ctx in meta:
            for scenario in COULEURS:
                donnees = toutes[ctx["sujet_id"]][scenario]
                variantes = [("", np.nanmean(donnees["oui_projete"], axis=0)),
                             ("mediane", np.nanmedian(donnees["oui_projete"], axis=0)),
                             ("depouillement",
                              np.nanmean(donnees["oui_depouille"], axis=0))]
                if scenario == "realiste" and donnees["oui_projete"].shape[0] > 1:
                    haut = np.nanpercentile(donnees["oui_projete"], 97.5, axis=0)
                    bas = np.nanpercentile(donnees["oui_projete"], 2.5, axis=0)
                    enveloppe = np.where(
                        np.abs(haut - ctx["vrai_oui"]) >= np.abs(bas - ctx["vrai_oui"]),
                        haut, bas)
                    variantes.append(("enveloppe", enveloppe))
                levier = np.nanmean(donnees["levier_max"], axis=0)
                for suffixe, courbe in variantes:
                    # Signé : sépare le biais (systématique) de la dispersion.
                    ecart = (courbe - ctx["vrai_oui"]) * 100
                    erreur = np.abs(ecart)
                    lignes.append({
                        "date": ctx["date"], "sujet": ctx["sujet_id"],
                        "nom": ctx["nom"][:70],
                        "scenario": scenario + ("_" + suffixe if suffixe else ""),
                        "vrai_oui_pct": round(100 * ctx["vrai_oui"], 3),
                        "erreur_max_pts": round(np.nanmax(erreur), 3),
                        "hors_cadre": int(np.nansum(erreur > 100 * marge)),
                        "avance_err_1pt": round(self.avance_sous(grille_avance, erreur, 1.0), 4),
                        "avance_err_0_5pt": round(self.avance_sous(grille_avance, erreur, 0.5), 4),
                        "erreur_a_10pct": round(float(np.interp(0.10, grille_avance, erreur)), 3),
                        "erreur_a_25pct": round(float(np.interp(0.25, grille_avance, erreur)), 3),
                        "erreur_a_50pct": round(float(np.interp(0.50, grille_avance, erreur)), 3),
                        "biais_a_10pct": round(float(np.interp(0.10, grille_avance, ecart)), 3),
                        "biais_a_25pct": round(float(np.interp(0.25, grille_avance, ecart)), 3),
                        "biais_a_50pct": round(float(np.interp(0.50, grille_avance, ecart)), 3),
                        "avance_levier_sous_seuil":
                            round(self.avance_levier_sous(grille_avance, levier, seuil), 4),
                        "nb_communes": ctx["nb_communes"],
                        "nb_objets_acp": ctx["nb_objets_acp"],
                    })
        chemin = sortie / "synthese.csv"
        with open(chemin, "w", newline="") as fichier:
            plume = csv.DictWriter(fichier, fieldnames=list(lignes[0]))
            plume.writeheader()
            plume.writerows(lignes)
        self.journal(f"Table de synthèse : {chemin}")
        return lignes

    def figures(self, sortie, meta, toutes, grille_avance, options):
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        marge = options["marge_graphique"] / 100
        for ctx in meta:
            figure, axe = plt.subplots(figsize=(7, 4.5))
            self.tracer(axe, ctx, toutes[ctx["sujet_id"]], grille_avance, marge)
            axe.set_xlabel("avance (part des bulletins dépouillés)")
            axe.set_ylabel("% oui projeté")
            axe.legend(fontsize=6)
            figure.tight_layout()
            for suffixe in ("png", "pdf"):
                figure.savefig(sortie / f"objet_{ctx['sujet_id']:03d}.{suffixe}", dpi=110)
            plt.close(figure)

        colonnes = 5
        rangees = int(np.ceil(len(meta) / colonnes))
        figure, axes = plt.subplots(rangees, colonnes,
                                    figsize=(3.2 * colonnes, 2.4 * rangees))
        for axe, ctx in zip(np.ravel(axes), meta):
            self.tracer(axe, ctx, toutes[ctx["sujet_id"]], grille_avance, marge, compact=True)
        for axe in np.ravel(axes)[len(meta):]:
            axe.axis("off")
        figure.tight_layout()
        for suffixe in ("png", "pdf"):
            figure.savefig(sortie / f"recapitulatif.{suffixe}", dpi=100)
        plt.close(figure)
        self.figure_biais(sortie, meta, toutes, grille_avance, plt)
        self.journal(f"Figures : {sortie}/objet_*.{{png,pdf}}, recapitulatif.{{png,pdf}} "
                     f"et biais_agrege.{{png,pdf}}")

    def figure_biais(self, sortie, meta, toutes, grille_avance, plt):
        """Biais signé médian sur les 30 objets — ce qu'un panneau seul ne montre pas.

        Chaque figure par objet mélange biais et dispersion ; seule l'agrégation
        signée dit si un scénario décale systématiquement la projection.
        """
        figure, (haut, bas) = plt.subplots(2, 1, figsize=(8, 8), sharex=True)
        for axe, cle, titre in (
                (haut, "oui_projete", "Extrapolation"),
                (bas, "oui_depouille", "Dépouillement nu (sans extrapolation)")):
            for scenario, couleur in COULEURS.items():
                ecarts = np.array([
                    np.nanmean(toutes[ctx["sujet_id"]][scenario][cle], axis=0)
                    - ctx["vrai_oui"] for ctx in meta]) * 100
                axe.plot(grille_avance, np.nanmedian(ecarts, axis=0), color=couleur,
                         lw=1.4, label=scenario.replace("_", " "))
                axe.fill_between(grille_avance,
                                 np.nanpercentile(ecarts, 25, axis=0),
                                 np.nanpercentile(ecarts, 75, axis=0),
                                 color=couleur, alpha=0.12, lw=0)
            axe.axhline(0, color="black", ls=":", lw=1.1)
            axe.set_ylim(-12, 12)
            axe.set_xlim(0, 1)
            axe.set_ylabel("biais signé (points de %oui)")
            axe.set_title(f"{titre} — médiane signée sur {len(meta)} objets, "
                          "bande = quartiles", fontsize=9)
            axe.legend(fontsize=7)
        bas.set_xlabel("avance (part des bulletins dépouillés)")
        figure.tight_layout()
        for suffixe in ("png", "pdf"):
            figure.savefig(sortie / f"biais_agrege.{suffixe}", dpi=110)
        plt.close(figure)

    def tracer(self, axe, ctx, courbes, grille_avance, marge, compact=False):
        vrai = 100 * ctx["vrai_oui"]
        for scenario, couleur in COULEURS.items():  # noqa: B007
            donnees = courbes[scenario]["oui_projete"] * 100
            moyenne = np.nanmean(donnees, axis=0)
            axe.plot(grille_avance, moyenne, color=couleur, lw=1.2,
                     label=scenario.replace("_", " "))
            nu = np.nanmean(courbes[scenario]["oui_depouille"], axis=0) * 100
            axe.plot(grille_avance, nu, color=couleur, lw=1.0, ls="--", alpha=0.55,
                     label=None if compact else
                     scenario.replace("_", " ") + " — dépouillement nu")
            if scenario == "realiste" and donnees.shape[0] > 1:
                axe.fill_between(grille_avance,
                                 np.nanpercentile(donnees, 2.5, axis=0),
                                 np.nanpercentile(donnees, 97.5, axis=0),
                                 color=couleur, alpha=0.2, lw=0)
        axe.axhline(vrai, color="black", ls=":", lw=1.1,
                    label=None if compact else f"résultat final {vrai:.2f}%")
        axe.set_ylim(vrai - 100 * marge, vrai + 100 * marge)
        axe.set_xlim(0, 1)
        titre = (f"{ctx['date']} — {ctx['nom'][:46]}\n"
                 f"oui {vrai:.2f}% · {ctx['nb_objets_acp']} objets ACP")
        axe.set_title(titre, fontsize=7 if compact else 9)
        if compact:
            axe.tick_params(labelsize=6)

    def resume(self, table, meta, toutes, grille_avance, seuil):
        self.journal("\n=== Synthèse (médianes sur les cibles) ===")
        self.journal(f"seuil de levier calibré : {seuil:.3g}")
        entete = (f"{'scénario':26} {'err max':>8} {'err@10%':>8} {'err@50%':>8} "
                  f"{'biais@10%':>10} {'biais@50%':>10} {'sous':>5} {'a<1pt':>7} {'a levier':>9}")
        self.journal(entete)
        for scenario in sorted({ligne["scenario"] for ligne in table}):
            sous_ens = [ligne for ligne in table if ligne["scenario"] == scenario]
            def med(cle):
                valeurs = [ligne[cle] for ligne in sous_ens if not np.isnan(ligne[cle])]
                return np.median(valeurs) if valeurs else np.nan
            sous = np.mean([ligne["biais_a_10pct"] < 0 for ligne in sous_ens])
            self.journal(f"{scenario:26} {med('erreur_max_pts'):8.2f} {med('erreur_a_10pct'):8.2f} "
                         f"{med('erreur_a_50pct'):8.2f} {med('biais_a_10pct'):10.2f} "
                         f"{med('biais_a_50pct'):10.2f} {sous:5.0%} "
                         f"{med('avance_err_1pt'):7.3f} "
                         f"{med('avance_levier_sous_seuil'):9.3f}")

        rejoints = []
        for ctx in meta:
            courbes = toutes[ctx["sujet_id"]]
            ecart = np.abs(courbes["adversarial_bas"]["oui_projete"][0]
                           - courbes["adversarial_haut"]["oui_projete"][0]) * 100
            rejoints.append(self.avance_sous(grille_avance, ecart, 1.0))
        valides = [x for x in rejoints if not np.isnan(x)]
        if valides:
            self.journal(f"\nLes deux adversariaux se rejoignent (écart < 1 point) à une avance "
                         f"médiane de {np.median(valides):.1%} "
                         f"[{np.min(valides):.1%} – {np.max(valides):.1%}]")

    # --------------------------------------------------------- équivalence

    def test_equivalence(self, options):
        import scipy.optimize

        from scrutin.extrapolation import Delta_fast
        sujets, communes, oui, non, elec, bul, cibles = self.preparer(options)
        rng = np.random.default_rng(options["graine"])
        cible = cibles[rng.integers(len(cibles))]
        ctx = self.contexte(cible, sujets, oui, non, elec, bul, {})
        nb = ctx["nb_communes"]
        masque = np.zeros(nb, dtype=bool)
        masque[rng.choice(nb, size=rng.integers(20, nb), replace=False)] = True
        self.journal(f"Objet tiré : {ctx['date']} — {ctx['nom'][:60]}")
        self.journal(f"Masque tiré : {masque.sum()} communes dépouillées sur {nb}")

        design = np.column_stack([ctx["composantes"], np.ones(nb)])[masque]
        poids = ctx["bulletins"][masque].astype(float)
        for etiquette, cible_y in (("%oui", ctx["pourcentage_oui"]),
                                   ("participation", ctx["participation"])):
            y = cible_y[masque]
            beta_lstsq = ajuster(design, y, poids)
            depart = np.full(NB_COMPOSANTES + 1, 0.0)
            depart[-1] = 0.5
            ajustement = scipy.optimize.minimize(
                Delta_fast, depart,
                args=(design[:, :-1], y, poids))
            ecart = np.abs(beta_lstsq - ajustement.x).max()
            self.journal(f"\n{etiquette} :")
            self.journal(f"  lstsq    {np.array2string(beta_lstsq, precision=6)}")
            self.journal(f"  minimize {np.array2string(ajustement.x, precision=6)}")
            self.journal(f"  écart max sur les 7 paramètres : {ecart:.3e}")
            self.journal(f"  Delta(lstsq)={Delta_fast(beta_lstsq, design[:, :-1], y, poids):.10g}  "
                         f"Delta(minimize)={ajustement.fun:.10g}")
            if ecart > 1e-6:
                self.journal(self.style.WARNING(
                    "  /!\\ écart > 1e-6 : minimize n'a pas convergé "
                    f"(succès={ajustement.success}, nit={ajustement.nit})"))

    # ------------------------------------------------------- garde-fou

    def analyse_garde_fou(self, options):
        """Le levier max prédit-il la fiabilité mieux que le compte de communes ?

        Relit courbes.csv.gz : chaque point est un instantané de soirée, étiqueté
        « fiable » si le %oui projeté est à moins d'un point du résultat final.
        """
        from array import array

        from sklearn.metrics import roc_auc_score

        sortie = Path(options["sortie"])
        vrai = {}
        with open(sortie / "synthese.csv") as fichier:
            for ligne in csv.DictReader(fichier):
                vrai[int(ligne["sujet"])] = float(ligne["vrai_oui_pct"])

        erreur, levier, communes, avance, scenarios = (array("d"), array("d"),
                                                       array("d"), array("d"), [])
        with gzip.open(sortie / "courbes.csv.gz", "rt") as fichier:
            for ligne in csv.DictReader(fichier):
                valeur = float(ligne["levier_max"])
                if not np.isfinite(valeur):
                    continue
                erreur.append(abs(100 * float(ligne["oui_projete"]) - vrai[int(ligne["sujet"])]))
                levier.append(valeur)
                communes.append(float(ligne["nb_depouillees"]))
                avance.append(float(ligne["avance"]))
                scenarios.append(ligne["scenario"])

        erreur, levier = np.array(erreur), np.array(levier)
        communes, avance = np.array(communes), np.array(avance)
        scenarios = np.array(scenarios)
        fiable = erreur < 1.0
        self.journal(f"{len(erreur)} instantanés, dont {100*fiable.mean():.1f} % à moins d'un point")

        predicteurs = {"levier max (faible = bon)": -levier,
                       "communes dépouillées": communes,
                       "avance": avance}
        for sous_ensemble in ("tous scénarios", "réaliste seul"):
            garde = np.ones(len(erreur), bool) if sous_ensemble == "tous scénarios" \
                else scenarios == "realiste"
            self.journal(f"\n--- {sous_ensemble} ({garde.sum()} points) ---")
            self.journal(f"{'prédicteur':28} {'AUC':>6} {'seuil 95% fiable':>18} {'couverture':>11}")
            for nom, score in predicteurs.items():
                aire = roc_auc_score(fiable[garde], score[garde])
                seuil, couverture = self.seuil_precision(score[garde], fiable[garde], 0.95)
                brut = -seuil if nom.startswith("levier") else seuil
                self.journal(f"{nom:28} {aire:6.3f} {brut:18.4g} {couverture:10.1%}")

    @staticmethod
    def seuil_precision(score, fiable, precision):
        """Seuil le plus permissif dont la précision atteint la cible."""
        tri = np.argsort(-score, kind="stable")
        cumul = np.cumsum(fiable[tri])
        rangs = np.arange(1, len(tri) + 1)
        atteint = np.where(cumul / rangs >= precision)[0]
        if len(atteint) == 0:
            return np.nan, 0.0
        dernier = atteint[-1]
        return float(score[tri][dernier]), cumul[dernier] / fiable.sum()

    # ------------------------------------------------------ mécanisme

    def figure_mecanisme(self, options):
        """Le modèle corrige le profil, pas le résidu.

        En abscisse la prédiction du modèle ajusté sur *toutes* les communes :
        les 6 dimensions de l'ACP s'y résument en une seule, et la droite de
        référence est la première bissectrice.
        """
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        sortie = Path(options["sortie"])
        sujets, communes, oui, non, elec, bul, cibles = self.preparer(options)
        ctx = self.contexte(cibles[18], sujets, oui, non, elec, bul, {})
        nb = ctx["nb_communes"]
        design = np.column_stack([ctx["composantes"], np.ones(nb)])
        poids = ctx["bulletins"].astype(float)
        beta = ajuster(design, ctx["pourcentage_oui"], poids)
        prediction = design @ beta * 100          # ce que le profil ACP prédit
        reel = ctx["pourcentage_oui"] * 100

        figure, axes = plt.subplots(1, 2, figsize=(11, 5), sharey=True, sharex=True)
        cible_bulletins = 0.10 * ctx["exprimes"].sum()
        for axe, scenario, couleur in ((axes[0], "adversarial_bas", "tab:red"),
                                       (axes[1], "profil_bas", "tab:purple")):
            ordre = ordres(scenario, ctx["pourcentage_oui"], ctx["composantes"],
                           ctx["electeurs"], np.random.default_rng(0))
            k = int(np.searchsorted(np.cumsum(ctx["exprimes"][ordre]), cible_bulletins)) + 1
            pris = ordre[:k]
            axe.scatter(prediction, reel, s=3, color="lightgrey", label="toutes les communes")
            axe.scatter(prediction[pris], reel[pris], s=6, color=couleur,
                        label=f"dépouillées à 10 % ({k} communes)")
            bornes = np.array([prediction.min(), prediction.max()])
            axe.plot(bornes, bornes, color="black", lw=1.2,
                     label="modèle ajusté sur toutes")
            bp = ajuster(design[pris], ctx["pourcentage_oui"][pris], poids[pris])
            axe.plot(bornes, np.polyval(np.polyfit(prediction[pris],
                                                   design[pris] @ bp * 100, 1), bornes),
                     color=couleur, lw=1.6, ls="--",
                     label="modèle ajusté sur les dépouillées")
            residu = np.average(reel[pris] - prediction[pris], weights=poids[pris])
            axe.set_title(f"{scenario.replace('_', ' ')}\n"
                          f"résidu moyen des dépouillées : {residu:+.2f} pt", fontsize=10)
            axe.set_xlabel("%oui prédit par le profil ACP")
            axe.legend(fontsize=7, loc="upper left")
        axes[0].set_ylabel("%oui réellement observé")
        figure.suptitle(f"{ctx['date']} — {ctx['nom'][:60]}", fontsize=10)
        figure.tight_layout()
        for suffixe in ("png", "pdf"):
            figure.savefig(sortie / f"mecanisme.{suffixe}", dpi=110)
        plt.close(figure)
        self.journal(f"Figure : {sortie}/mecanisme.{{png,pdf}}")
