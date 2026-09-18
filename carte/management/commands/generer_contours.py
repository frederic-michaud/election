"""Fabrique le fond de carte statique : ``communes.geojson`` et ``lacs.geojson``.

Deux sources, hors dépôt, à passer en arguments :

1. Le GeoPackage **swissBOUNDARIES3D** de swisstopo, en LV95 — un fichier
   SQLite, donc lisible sans dépendance (37 Mo zippés) :
   ``https://data.geo.admin.ch/ch.swisstopo.swissboundaries3d/swissboundaries3d_2026-01/swissboundaries3d_2026-01_2056_5728.gpkg.zip``
   Le millésime suivant se retrouve par l'API STAC, collection
   ``ch.swisstopo.swissboundaries3d``.
2. Le **TopoJSON de l'OFS** (celui d'où venait l'ancien fond), pour ses lacs :
   ``https://dam-api.bfs.admin.ch/hub/api/dam/assets/36438312/master``
   Le millésime suivant se retrouve par l'API CKAN d'opendata.swiss, jeu
   ``geodaten-zu-den-eidgenoessischen-abstimmungsvorlagen``.

Les fichiers produits sont committés : cette commande ne resert qu'au
changement de millésime.

Pourquoi ne plus prendre les communes chez l'OFS : son fond est *généralisé* à
onze sommets par commune, d'où des contours anguleux, et il manquait quatorze
communes. swissBOUNDARIES3D en a 459 par commune, qu'on ramène ici à la
tolérance demandée.

La simplification **garde la topologie** : chaque frontière partagée est
découpée aux jonctions, puis simplifiée une seule fois pour les deux communes
qui la bordent. Sans cela, Douglas-Peucker ne les traiterait pas de la même
façon et un liseré blanc apparaîtrait entre voisines.

Les lacs viennent de l'OFS parce que swissBOUNDARIES3D n'en a pas : une commune
riveraine s'y étend jusqu'au milieu de l'eau. Ils sont donc peints par-dessus
les communes (``charte.habiller_carte``), comme les trous du fond précédent.
"""

import json
import math
import sqlite3
import struct
from pathlib import Path

from django.core.management.base import BaseCommand

DOSSIER = Path("carte/static/carte")
TOLERANCE = 25      # mètres : ~140 sommets par commune
DECIMALES = 5       # ~1 m, bien en deçà de la tolérance

# Longueur de l'en-tête d'un blob GeoPackage selon son code d'enveloppe.
ENVELOPPE = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}


def polygones(blob):
    """Les anneaux du MultiPolygon d'un blob GeoPackage, en LV95 et sans Z."""
    tampon = memoryview(blob)[8 + ENVELOPPE[(blob[3] >> 1) & 7]:]

    def anneaux(position, ordre, dimensions):
        (n,) = struct.unpack_from(ordre + "I", tampon, position)
        position += 4
        sortie = []
        for _ in range(n):
            (m,) = struct.unpack_from(ordre + "I", tampon, position)
            position += 4
            plat = struct.unpack_from(f"{ordre}{m * dimensions}d", tampon, position)
            position += 8 * m * dimensions
            sortie.append([(plat[i * dimensions], plat[i * dimensions + 1]) for i in range(m)])
        return position, sortie

    ordre = "<" if tampon[0] else ">"
    (type_,) = struct.unpack_from(ordre + "I", tampon, 1)
    position, sortie = 5, []
    if type_ % 1000 == 3:
        _, rings = anneaux(position, ordre, 3 if type_ >= 1000 else 2)
        return [rings]
    (n,) = struct.unpack_from(ordre + "I", tampon, position)
    position += 4
    for _ in range(n):
        ordre_partie = "<" if tampon[position] else ">"
        (type_partie,) = struct.unpack_from(ordre_partie + "I", tampon, position + 1)
        position, rings = anneaux(position + 5, ordre_partie,
                                  3 if type_partie >= 1000 else 2)
        sortie.append(rings)
    return sortie


def douglas_peucker(points, tolerance):
    """Simplification classique, dépliée en boucle : la récursion déborde."""
    if len(points) < 3:
        return points
    garde = [False] * len(points)
    garde[0] = garde[-1] = True
    pile = [(0, len(points) - 1)]
    while pile:
        debut, fin = pile.pop()
        if fin <= debut + 1:
            continue
        x1, y1 = points[debut]
        x2, y2 = points[fin]
        dx, dy = x2 - x1, y2 - y1
        norme = math.hypot(dx, dy)
        pire, coupure = 0.0, -1
        for i in range(debut + 1, fin):
            x, y = points[i]
            ecart = (abs(dy * x - dx * y + x2 * y1 - y2 * x1) / norme if norme
                     else math.hypot(x - x1, y - y1))
            if ecart > pire:
                pire, coupure = ecart, i
        if pire > tolerance:
            garde[coupure] = True
            pile += [(debut, coupure), (coupure, fin)]
    return [p for p, g in zip(points, garde) if g]


def wgs84(point):
    """LV95 → WGS84 par les formules approchées de swisstopo (justes au mètre)."""
    y = (point[0] - 2600000) / 1e6
    x = (point[1] - 1200000) / 1e6
    lon = 2.6779094 + 4.728982 * y + 0.791484 * y * x + 0.1306 * y * x * x - 0.0436 * y ** 3
    lat = (16.9023892 + 3.238272 * x - 0.270978 * y * y - 0.002528 * x * x
           - 0.0447 * y * y * x - 0.0140 * x ** 3)
    return round(lon * 100 / 36, DECIMALES), round(lat * 100 / 36, DECIMALES)


def _cle(point):
    """Le sommet au centimètre près, en un entier : les frontières partagées
    portent les mêmes coordonnées des deux côtés."""
    return (int(round(point[0] * 100)) << 32) | (int(round(point[1] * 100)) & 0xFFFFFFFF)


class Simplificateur:
    """Simplifie les anneaux en traitant chaque frontière partagée une seule fois."""

    def __init__(self, communes, tolerance):
        self.tolerance = tolerance
        self.deja_vues = {}
        self.occurrences = {}
        for anneau in self._tous_les_anneaux(communes):
            for point in anneau[:-1]:
                cle = _cle(point)
                self.occurrences[cle] = self.occurrences.get(cle, 0) + 1

    @staticmethod
    def _tous_les_anneaux(communes):
        for polygones_ in communes.values():
            for polygone in polygones_:
                yield from polygone

    def _chaine(self, chaine):
        """Une portion de frontière, simplifiée puis mise en cache.

        La clé ne change pas quand on la parcourt à l'envers — c'est le cas
        d'une frontière vue depuis l'autre commune.
        """
        cle = (len(chaine), _cle(chaine[0]) + _cle(chaine[-1]),
               sum(_cle(p) for p in chaine))
        if cle not in self.deja_vues:
            self.deja_vues[cle] = (_cle(chaine[0]),
                                   [wgs84(p) for p in douglas_peucker(chaine, self.tolerance)])
        depart, points = self.deja_vues[cle]
        return points if depart == _cle(chaine[0]) else points[::-1]

    def anneau(self, anneau):
        points = anneau[:-1]
        jonctions = [i for i, p in enumerate(points) if self.occurrences[_cle(p)] != 2]
        if not jonctions:
            # Aucune jonction : anneau entier (île, ou commune enclavée dans une
            # seule voisine). On le fait toujours partir du même sommet, sinon
            # les deux communes ne le simplifieraient pas pareil.
            depart = min(range(len(points)), key=lambda i: _cle(points[i]))
            tourne = points[depart:] + points[:depart]
            sortie = self._chaine(tourne + [tourne[0]])
        else:
            sortie = []
            for debut, fin in zip(jonctions, jonctions[1:] + [jonctions[0] + len(points)]):
                morceau = [points[i % len(points)] for i in range(debut, fin + 1)]
                sortie += self._chaine(morceau)[:-1]
            sortie.append(sortie[0])
        # L'arrondi peut confondre deux sommets voisins ; un anneau qui n'a plus
        # de surface est jeté.
        propre = [sortie[0]]
        for point in sortie[1:]:
            if point != propre[-1]:
                propre.append(point)
        if propre[0] != propre[-1]:
            propre.append(propre[0])
        return propre if len(propre) >= 4 else None


def lacs(topojson):
    """Les 23 lacs du TopoJSON de l'OFS, décodés et projetés en WGS84."""
    with open(topojson) as fichier:
        topo = json.load(fichier)
    echelle, origine = topo["transform"]["scale"], topo["transform"]["translate"]
    arcs = []
    for arc in topo["arcs"]:
        x = y = 0
        points = []
        for dx, dy in arc:
            x, y = x + dx, y + dy
            points.append(wgs84((x * echelle[0] + origine[0], y * echelle[1] + origine[1])))
        arcs.append(points)

    def anneau(indices):
        points = []
        for indice in indices:
            arc = arcs[~indice][::-1] if indice < 0 else arcs[indice]
            points += arc[:-1]
        return points + [points[0]]

    entites = []
    for geometrie in topo["objects"]["K4seen_yyymmdd11"]["geometries"]:
        if geometrie["type"] == "Polygon":
            coordonnees = [anneau(r) for r in geometrie["arcs"]]
        else:
            coordonnees = [[anneau(r) for r in p] for p in geometrie["arcs"]]
        entites.append({
            "type": "Feature",
            "properties": {"nom": geometrie["properties"]["name"]},
            "geometry": {"type": geometrie["type"], "coordinates": coordonnees},
        })
    return entites


def ecrire(entites, chemin):
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with open(chemin, "w") as fichier:
        json.dump({"type": "FeatureCollection", "features": entites}, fichier,
                  separators=(",", ":"), ensure_ascii=False)


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument("gpkg", type=Path, help="GeoPackage swissBOUNDARIES3D (LV95)")
        parser.add_argument("topojson", type=Path, help="TopoJSON de l'OFS, pour les lacs")
        parser.add_argument("dossier", nargs="?", default=DOSSIER, type=Path)
        parser.add_argument("--tolerance", type=float, default=TOLERANCE,
                            help=f"Tolérance de simplification, en mètres (défaut : {TOLERANCE}).")

    def handle(self, gpkg, topojson, dossier, tolerance, **options):
        communes, noms = {}, {}
        base = sqlite3.connect(gpkg)
        # ``icc`` écarte le Liechtenstein, Büsingen et Campione, présents dans
        # la source ; ``objektart`` écarte les plans d'eau et les communances.
        requete = ("select bfs_nummer, name, geom from tlm_hoheitsgebiet "
                   "where objektart = 'Gemeindegebiet' and icc = 'CH'")
        for ofs, nom, blob in base.execute(requete):
            communes.setdefault(ofs, []).extend(polygones(blob))
            noms[ofs] = nom

        simplificateur = Simplificateur(communes, tolerance)
        entites, sommets = [], 0
        for ofs in sorted(communes):
            polygones_ = []
            for polygone in communes[ofs]:
                anneaux = [a for a in (simplificateur.anneau(r) for r in polygone) if a]
                if anneaux:
                    polygones_.append(anneaux)
            sommets += sum(len(a) for p in polygones_ for a in p)
            geometrie = ({"type": "Polygon", "coordinates": polygones_[0]} if len(polygones_) == 1
                         else {"type": "MultiPolygon", "coordinates": polygones_})
            entites.append({"type": "Feature",
                            "properties": {"vogeId": ofs, "vogeName": noms[ofs]},
                            "geometry": geometrie})

        cible = dossier / "communes.geojson"
        ecrire(entites, cible)
        self.stdout.write(f"{len(entites)} communes, {sommets} sommets "
                          f"({sommets // len(entites)} par commune en moyenne) "
                          f"→ {cible} ({cible.stat().st_size // 1000} ko)")

        cible_lacs = dossier / "lacs.geojson"
        entites_lacs = lacs(topojson)
        ecrire(entites_lacs, cible_lacs)
        self.stdout.write(f"{len(entites_lacs)} lacs → {cible_lacs} "
                          f"({cible_lacs.stat().st_size // 1000} ko)")
        self.stdout.write(f"emprise : {emprise(entites)}")


def emprise(entites):
    """((lon min, lat min), (lon max, lat max)) — recopiée dans ``carte.API``."""
    def points(coordonnees):
        if isinstance(coordonnees[0], (int, float)):
            yield coordonnees
        else:
            for c in coordonnees:
                yield from points(c)

    lon, lat = zip(*(p for e in entites for p in points(e["geometry"]["coordinates"])))
    return (min(lon), min(lat)), (max(lon), max(lat))
