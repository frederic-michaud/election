"""Reconstruit l'historique communal depuis le cube STAT-TAB de l'OFS.

Le cube « Votations populaires, résultats au niveau des communes depuis 1960 »
(px-x-1703030000_101) publie chaque objet fédéral **harmonisé sur les communes
actuelles** : une commune fusionnée porte les voix de ses prédécesseurs.
L'appariement se fait donc par numéro OFS, exactement comme le jour J.

    python manage.py importer_historique --depuis 2014-11-30

Seuls les objets votés depuis `--depuis` sont gardés : les profils de commune
doivent refléter le vote d'aujourd'hui, pas celui d'il y a vingt ans. Depuis le
30 novembre 2014, les douze pseudo-communes « étranger » sont toutes publiées.

API PX-Web JSON, sans clé. Les objets sont demandés par lots de 10 : au-delà,
le pare-feu de l'OFS répond 403 (constaté le 2026-09-04, bien avant la limite
documentée de 2,5 M de cellules). Relançable : les résultats d'un objet sont
remplacés.

Les pseudo-communes « Suisses de l'étranger » (numéros OFS 9xxx) n'existent
que dans les résultats de votation, pas dans le répertoire des communes :
l'import les crée à la volée, rattachées à leur canton.
"""

import datetime
import json
import logging
import urllib.request

from django.core.management.base import BaseCommand
from django.db import transaction

from scrutin.models import Canton, Commune, District, ResultatCommunalHistorique, SujetVote

logger = logging.getLogger(__name__)

URL = "https://www.pxweb.bfs.admin.ch/api/v1/fr/px-x-1703030000_101/px-x-1703030000_101.px"
DIM_GEO = "Kanton (-) / Bezirk (>>) / Gemeinde (......)"
DIM_OBJET = "Datum und Vorlage"
DIM_RESULTAT = "Ergebnis"
# Codes de la dimension « Résultat » → champ de ResultatCommunalHistorique.
CHAMPS = {"1": "electeurs_inscrits", "2": "bulletins_rentres",
          "5": "nombre_oui", "6": "nombre_non"}
MANQUANT = "..."


def requete(corps=None):
    donnees = None if corps is None else json.dumps(corps).encode()
    req = urllib.request.Request(URL, data=donnees,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as reponse:
        return json.load(reponse)


def lire_metadonnees():
    """Renvoie ({code_objet: (date, nom)}, {numero_ofs: nom_commune}).

    Dans la dimension géographique, seules les valeurs à 4 caractères sont des
    communes (2 : Suisse et cantons, 6 : districts).
    """
    variables = {v["code"]: v for v in requete()["variables"]}
    objets = {}
    for code, texte in zip(variables[DIM_OBJET]["values"], variables[DIM_OBJET]["valueTexts"]):
        objets[code] = (datetime.date.fromisoformat(texte[:10]), texte[11:])
    communes = {}
    for code, texte in zip(variables[DIM_GEO]["values"], variables[DIM_GEO]["valueTexts"]):
        if len(code) == 4:
            communes[int(code)] = texte.lstrip(".")
    return objets, communes


def lire_resultats(codes_objets):
    """Toutes les communes × ces objets → liste de (geo, objet, résultat, valeur)."""
    corps = {"query": [
        {"code": DIM_GEO, "selection": {"filter": "all", "values": ["*"]}},
        {"code": DIM_OBJET, "selection": {"filter": "item", "values": list(codes_objets)}},
        {"code": DIM_RESULTAT, "selection": {"filter": "item", "values": list(CHAMPS)}},
    ], "response": {"format": "json"}}
    return [(*ligne["key"], ligne["values"][0]) for ligne in requete(corps)["data"]]


def creer_pseudo_commune(numero_ofs, nom):
    """« VD-CH de l'étranger » → une commune du canton VD, dans son propre district."""
    canton = Canton.objects.get(abreviation=nom[:2])
    district, _ = District.objects.get_or_create(numero_ofs=numero_ofs, canton=canton,
                                                 defaults={"nom": nom})
    return Commune.objects.create(nom=nom, numero_ofs=numero_ofs, canton=canton,
                                  district=district)


@transaction.atomic
def enregistrer(codes, objets, noms_communes, lignes, communes):
    """Écrit un lot d'objets. Renvoie (nb résultats, numéros OFS inconnus)."""
    sujets = {}
    for code in codes:
        date, nom = objets[code]
        sujets[code], _ = SujetVote.objects.update_or_create(
            sujet_id=int(code), defaults={"nom": nom, "date": date})
    ResultatCommunalHistorique.objects.filter(sujet_vote__in=sujets.values()).delete()

    cellules = {}
    for geo, objet, resultat, valeur in lignes:
        if len(geo) == 4:
            cellules.setdefault((int(geo), objet), {})[CHAMPS[resultat]] = valeur

    resultats, inconnus = [], set()
    for (numero_ofs, objet), champs in cellules.items():
        if len(champs) < len(CHAMPS) or MANQUANT in champs.values():
            continue
        if numero_ofs not in communes:
            if numero_ofs < 9000:
                inconnus.add(numero_ofs)
                continue
            communes[numero_ofs] = creer_pseudo_commune(numero_ofs, noms_communes[numero_ofs])
        resultats.append(ResultatCommunalHistorique(
            commune=communes[numero_ofs], sujet_vote=sujets[objet],
            **{champ: int(valeur) for champ, valeur in champs.items()}))
    ResultatCommunalHistorique.objects.bulk_create(resultats, batch_size=1000)
    return len(resultats), inconnus


def importer(depuis, lot=10, rapport=print):
    """Charge tous les objets votés à partir de `depuis`, par lots."""
    objets, noms_communes = lire_metadonnees()
    codes = sorted((code for code, (date, _) in objets.items() if date >= depuis),
                   key=lambda code: objets[code][0])
    communes = {c.numero_ofs: c for c in Commune.objects.all()}
    total, inconnus = 0, set()
    for debut in range(0, len(codes), lot):
        codes_lot = codes[debut:debut + lot]
        lignes = lire_resultats(codes_lot)
        nb, inconnus_lot = enregistrer(codes_lot, objets, noms_communes, lignes, communes)
        total += nb
        inconnus |= inconnus_lot
        rapport(f"{objets[codes_lot[0]][0]} → {objets[codes_lot[-1]][0]} : "
                f"{len(codes_lot)} objets, {nb} résultats communaux")
    if inconnus:
        logger.warning("%d numéros OFS du cube absents de la base : %s",
                       len(inconnus), sorted(inconnus))
    SujetVote.objects.filter(date__lt=depuis).delete()
    return len(codes), total


class Command(BaseCommand):
    help = "Reconstruit l'historique communal depuis le cube STAT-TAB de l'OFS (réseau)."

    def add_arguments(self, parser):
        parser.add_argument("--depuis", type=datetime.date.fromisoformat,
                            default=datetime.date(2014, 11, 30),
                            help="premier scrutin gardé, AAAA-MM-JJ (défaut : 2014-11-30)")
        parser.add_argument("--lot", type=int, default=10,
                            help="objets par appel à l'API (défaut : 10, 403 au-delà)")

    def handle(self, *args, **options):
        nb_objets, nb_resultats = importer(options["depuis"], options["lot"],
                                           rapport=self.stdout.write)
        self.stdout.write(self.style.SUCCESS(
            f"{nb_objets} objets, {nb_resultats} résultats communaux"))
