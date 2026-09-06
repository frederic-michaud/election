"""Construit une base de démonstration à l'échelle réelle.

Toutes les communes suisses, un historique de votations et une soirée de
dépouillement en cours — le tout fictif, déterministe et fabriqué hors-ligne à
partir du GeoJSON déjà présent dans ``data/``.

Volontairement écrit **sans numpy ni scipy** : la voie Interface ne dispose que
de ``requirements/web.txt``, et doit pouvoir peupler sa base puis regarder le
site sans installer la pile scientifique.

Les votes ne sont pas du bruit blanc. Chaque commune reçoit un profil latent à
deux axes — urbain/rural et latin/alémanique — et chaque objet de votation ses
propres sensibilités à ces axes. L'ACP retrouve donc une vraie structure, et
l'extrapolation a quelque chose à apprendre : la démo exerce le pipeline, pas
seulement l'affichage.
"""

import datetime
import json
import math
import random

from django.core.management.base import BaseCommand
from django.db import transaction

from page_statique.models import PageStatique
from pca.models import PCAResult
from scrutin.models import (
    Canton,
    Commune,
    District,
    Extrapolation,
    ResultatCommunalEnCours,
    ResultatCommunalHistorique,
    SujetVote,
)

GRAINE = 20260825

NB_VOTATIONS_HISTORIQUES = 55
NB_OBJETS_JOUR_J = 3

# Part des communes déjà dépouillées au moment de l'instantané.
PART_DEPOUILLEE = 0.55

GEOJSON = "data/K4voge_20220501_gf.geojson"

# Numérotation OFS officielle des cantons. Le GeoJSON porte les noms
# alémaniques ; on garde les noms français, déjà utilisés dans le dépôt.
CANTONS = {
    1: ("ZH", "Zürich"), 2: ("BE", "Berne"), 3: ("LU", "Lucerne"),
    4: ("UR", "Uri"), 5: ("SZ", "Schwytz"), 6: ("OW", "Obwald"),
    7: ("NW", "Nidwald"), 8: ("GL", "Glaris"), 9: ("ZG", "Zoug"),
    10: ("FR", "Fribourg"), 11: ("SO", "Soleure"), 12: ("BS", "Bâle-Ville"),
    13: ("BL", "Bâle-Campagne"), 14: ("SH", "Schaffhouse"),
    15: ("AR", "Appenzell Rhodes-Extérieures"),
    16: ("AI", "Appenzell Rhodes-Intérieures"), 17: ("SG", "Saint-Gall"),
    18: ("GR", "Grisons"), 19: ("AG", "Argovie"), 20: ("TG", "Thurgovie"),
    21: ("TI", "Tessin"), 22: ("VD", "Vaud"), 23: ("VS", "Valais"),
    24: ("NE", "Neuchâtel"), 25: ("GE", "Genève"), 26: ("JU", "Jura"),
}

# Axe latin : 1 = francophone ou italophone, 0 = alémanique. Les cantons
# bilingues sont tirés commune par commune, dans les proportions réelles.
CANTONS_LATINS = {21, 22, 24, 25, 26}          # TI, VD, NE, GE, JU
CANTONS_BILINGUES = {10: 0.68, 23: 0.63, 2: 0.08}  # FR, VS, BE

THEMES = [
    "l'assurance-vieillesse", "la réforme fiscale", "l'initiative sur le climat",
    "la loi sur le CO2", "l'assurance-maladie", "la loi sur l'asile",
    "les transports publics", "la protection des données", "la loi sur l'énergie",
    "l'initiative pour les glaciers", "la réforme des retraites",
    "la loi sur la chasse", "le congé paternité", "l'initiative sur les soins",
    "la loi sur le cinéma", "l'agriculture durable", "la loi sur les stupéfiants",
    "l'initiative pour les Alpes", "la loi sur l'armée", "la naturalisation",
]
SIGLES = [
    "AVS 21", "RFFA", "CO2", "LAMal", "LAsi", "FAIF", "LPD", "LEne", "PV2030",
    "LChas", "APG", "LCin", "LStup", "LAAM", "LN", "LPP", "LSU", "LTr",
]


def sigmoide(x):
    return 1.0 / (1.0 + math.exp(-x))


def degre_urbanisation(urbanite):
    """Les trois degrés de DEGURB2021, dans des proportions proches du réel."""
    if urbanite > 1.5:
        return "urbain"
    if urbanite > 0:
        return "intermédiaire"
    return "rural"


class Command(BaseCommand):
    help = "Peuple la base avec des données fictives à l'échelle réelle."

    def add_arguments(self, parser):
        parser.add_argument(
            "--graine", type=int, default=GRAINE,
            help=f"Graine aléatoire (défaut : {GRAINE}).",
        )
        parser.add_argument(
            "--part-depouillee", type=float, default=PART_DEPOUILLEE,
            help=f"Part des communes dépouillées (défaut : {PART_DEPOUILLEE}).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        alea = random.Random(options["graine"])
        part_depouillee = options["part_depouillee"]

        self._vider()
        communes, profils = self._creer_communes(alea)
        self._creer_historique(alea, communes, profils)
        self._creer_jour_j(alea, communes, profils, part_depouillee)
        self._creer_pca(alea, communes, profils)
        self._creer_pages_statiques()

        self.stdout.write(self.style.SUCCESS(
            f"\nBase de démonstration prête : {len(communes)} communes, "
            f"{NB_VOTATIONS_HISTORIQUES} votations historiques, "
            f"{NB_OBJETS_JOUR_J} objets en cours de dépouillement.\n"
            "Lancez maintenant : python manage.py runserver"
        ))

    # ------------------------------------------------------------------ #

    def _vider(self):
        """Idempotence : on repart d'une base propre à chaque exécution."""
        for modele in (Extrapolation, ResultatCommunalEnCours, ResultatCommunalHistorique, PCAResult,
                       SujetVote, Commune, District, Canton, PageStatique):
            modele.objects.all().delete()

    def _creer_communes(self, alea):
        """Communes réelles (nom, numéro OFS, district, canton) + profil latent."""
        with open(GEOJSON) as f:
            geojson = json.load(f)

        cantons = {}
        districts = {}
        for entite in geojson["features"]:
            p = entite["properties"]
            if p["kantId"] not in cantons:
                abrev, nom = CANTONS[p["kantId"]]
                cantons[p["kantId"]] = Canton(abreviation=abrev, nom=nom)
            districts.setdefault(p["bezkId"], (p["bezkName"], p["kantId"]))

        Canton.objects.bulk_create(cantons.values())
        cantons = {c.abreviation: c for c in Canton.objects.all()}
        cantons = {
            id_: cantons[CANTONS[id_][0]] for id_ in CANTONS
            if CANTONS[id_][0] in cantons
        }

        District.objects.bulk_create([
            District(nom=nom, code_historique=id_, canton=cantons[id_canton])
            for id_, (nom, id_canton) in districts.items()
        ])
        districts_db = {d.code_historique: d for d in District.objects.all()}

        # Une composante par district : les profils voisins se ressemblent,
        # sinon la carte serait du poivre et sel et ne dirait rien.
        urbanite_district = {id_: alea.gauss(0, 0.7) for id_ in districts}

        communes, profils = [], {}
        for entite in geojson["features"]:
            p = entite["properties"]
            id_canton = p["kantId"]

            if id_canton in CANTONS_LATINS:
                latin = 1.0
            elif id_canton in CANTONS_BILINGUES:
                latin = 1.0 if alea.random() < CANTONS_BILINGUES[id_canton] else 0.0
            else:
                latin = 0.0

            urbanite = urbanite_district[p["bezkId"]] + alea.gauss(0, 0.7)
            # Log-normale — quelques grandes villes, une longue traîne de
            # petites communes. La taille est corrélée à l'urbanité : c'est ce
            # qui rend la démo intéressante, puisque les petites communes
            # dépouillent en premier. Sans cette corrélation, le dépouillement
            # partiel ne serait pas biaisé et l'extrapolation n'aurait rien à
            # corriger.
            electeurs = int(math.exp(alea.gauss(6.6 + 0.9 * urbanite, 0.85)))
            electeurs = max(25, min(electeurs, 250_000))

            communes.append(Commune(
                nom=p["vogeName"],
                numero_ofs=p["vogeId"],
                canton=cantons[id_canton],
                district=districts_db[p["bezkId"]],
                langue="français" if latin else "allemand",
                degre_urbanisation=degre_urbanisation(urbanite),
                nb_voix=electeurs,
            ))
            profils[p["vogeId"]] = (urbanite, latin, electeurs)

        Commune.objects.bulk_create(communes, batch_size=1000)
        communes = list(Commune.objects.all().order_by("numero_ofs"))
        self.stdout.write(f"  {len(communes)} communes")
        return communes, profils

    def _tirer_resultat(self, alea, profil, sensibilites):
        """Un résultat de commune pour un objet donné, via le profil latent."""
        urbanite, latin, electeurs = profil
        base, a_urbain, a_latin, base_part = sensibilites

        p_oui = sigmoide(base + a_urbain * urbanite + a_latin * latin
                         + alea.gauss(0, 0.25))
        # Les petites communes participent davantage — c'est le cas en Suisse.
        participation = sigmoide(base_part - 0.12 * urbanite + alea.gauss(0, 0.2))

        votants = max(1, int(electeurs * participation))
        oui = int(round(votants * p_oui))
        return oui, votants - oui, votants

    def _sensibilites(self, alea):
        return (
            alea.gauss(0, 0.8),    # tendance nationale
            alea.gauss(0, 0.6),    # sensibilité urbain/rural
            alea.gauss(0, 0.6),    # sensibilité latin/alémanique (Röstigraben)
            alea.gauss(0.05, 0.3),  # niveau de participation
        )

    def _creer_historique(self, alea, communes, profils):
        """Les votations passées : la matrice qui alimente l'ACP."""
        debut = datetime.date.today() - datetime.timedelta(days=365 * 14)
        sujets = []
        for i in range(NB_VOTATIONS_HISTORIQUES):
            theme = THEMES[i % len(THEMES)]
            sigle = SIGLES[i % len(SIGLES)]
            sujets.append(SujetVote(
                nom=f"Votation sur {theme} ({sigle}-{i + 1})",
                sujet_id=i + 1,
                date=debut + datetime.timedelta(days=91 * i),
            ))
        SujetVote.objects.bulk_create(sujets)
        sujets = list(SujetVote.objects.order_by("date"))

        voix = []
        for sujet in sujets:
            sensibilites = self._sensibilites(alea)
            for commune in communes:
                oui, non, votants = self._tirer_resultat(
                    alea, profils[commune.numero_ofs], sensibilites)
                voix.append(ResultatCommunalHistorique(
                    commune=commune, sujet_vote=sujet,
                    nombre_oui=oui, nombre_non=non,
                    electeurs_inscrits=profils[commune.numero_ofs][2],
                    bulletins_rentres=votants,
                ))
        ResultatCommunalHistorique.objects.bulk_create(voix, batch_size=5000)
        self.stdout.write(f"  {len(voix)} résultats historiques "
                          f"({len(sujets)} votations)")

    def _creer_jour_j(self, alea, communes, profils, part_depouillee):
        """La soirée en cours : une partie des communes seulement est rentrée."""
        jour = datetime.date.today()
        base_id = NB_VOTATIONS_HISTORIQUES
        sujets = SujetVote.objects.bulk_create([
            SujetVote(
                nom=f"Votation sur {THEMES[-(i + 1)]} ({SIGLES[-(i + 1)]})",
                sujet_id=base_id + i + 1,
                date=jour,
            )
            for i in range(NB_OBJETS_JOUR_J)
        ])
        sujets = list(SujetVote.objects.filter(date=jour).order_by("sujet_id"))

        # Les petites communes dépouillent en premier : c'est précisément le
        # biais que l'extrapolation doit corriger.
        ordre = sorted(communes, key=lambda c: profils[c.numero_ofs][2])
        nb_comptees = int(len(ordre) * part_depouillee)
        comptees = {c.numero_ofs for c in ordre[:nb_comptees]}

        lignes, extrapolations = [], []
        for sujet in sujets:
            sensibilites = self._sensibilites(alea)
            oui_compte = non_compte = oui_total = non_total = 0

            for commune in communes:
                oui, non, votants = self._tirer_resultat(
                    alea, profils[commune.numero_ofs], sensibilites)
                est_comptee = commune.numero_ofs in comptees

                oui_total += oui
                non_total += non
                if est_comptee:
                    oui_compte += oui
                    non_compte += non

                # Les communes non dépouillées portent quand même une valeur :
                # c'est ce que run_extrapolation écrit en vrai, et ce qui
                # permet aux cartes d'afficher toute la Suisse.
                lignes.append(ResultatCommunalEnCours(
                    commune=commune, sujet_vote=sujet,
                    nombre_oui=oui, nombre_non=non,
                    electeurs_inscrits=profils[commune.numero_ofs][2],
                    bulletins_rentres=votants,
                    electeur_election_precedente=profils[commune.numero_ofs][2],
                    comptabilise=est_comptee,
                ))

            connu = oui_compte / max(1, oui_compte + non_compte)
            reel = oui_total / max(1, oui_total + non_total)
            # Une projection plausible : proche du résultat réel, jamais exacte.
            extrapolations.append(Extrapolation(
                sujet_vote=sujet,
                pourcentage_oui_connu=connu,
                pourcentage_oui_extrapole=reel + alea.gauss(0, 0.004),
                avance=(oui_compte + non_compte) / max(1, oui_total + non_total),
            ))

        ResultatCommunalEnCours.objects.bulk_create(lignes, batch_size=5000)
        Extrapolation.objects.bulk_create(extrapolations)
        self.stdout.write(
            f"  {len(lignes)} lignes de scrutin en cours "
            f"({nb_comptees}/{len(communes)} communes dépouillées)")

    def _creer_pages_statiques(self):
        """Les pages du menu, sinon les onglets tombent en 404 sur un clone frais.

        Contenu volontairement squelettique : la vraie page « Méthodes » est
        écrite en base, page par page (PLAN_MODERNISATION.md, D1).
        """
        PageStatique.objects.bulk_create([
            PageStatique(
                titre="Méthodes",
                url="methode",
                ordre=1,
                contenu="<p>Page de démonstration. La méthode réelle est décrite "
                        "dans le README : ACP sur l'historique communal, puis "
                        "régression pondérée sur les communes déjà dépouillées.</p>",
            ),
            PageStatique(
                titre="Contact",
                url="contact",
                ordre=2,
                contenu="<p>Page de démonstration.</p>",
            ),
        ])
        self.stdout.write("  2 pages statiques (menu)")

    def _creer_pca(self, alea, communes, profils):
        """Coordonnées ACP cohérentes avec le profil latent.

        On les fabrique directement plutôt que de les calculer : peupler_demo
        doit tourner sans scikit-learn. Les deux premiers axes portent la vraie
        structure — c'est ce qu'une ACP sur la matrice historique retrouverait.
        """
        PCAResult.objects.bulk_create([
            PCAResult(
                commune=commune,
                coordinate_1=profils[commune.numero_ofs][0],
                coordinate_2=profils[commune.numero_ofs][1] - 0.35,
                coordinate_3=alea.gauss(0, 0.3),
                coordinate_4=alea.gauss(0, 0.2),
                coordinate_5=alea.gauss(0, 0.15),
                coordinate_6=alea.gauss(0, 0.1),
            )
            for commune in communes
        ], batch_size=1000)
        self.stdout.write(f"  {len(communes)} profils ACP")
