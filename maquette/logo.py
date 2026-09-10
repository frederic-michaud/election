"""Le logo de la maquette, tiré des vrais contours communaux.

L'emblème du site — la Suisse, des barres qui en sortent, « Politiques.ch » —
est un PNG gris et bleu ciel (`scrutin/static/scrutin/logo.png`). La maquette
en refait une version SVG dans sa palette, posée en ligne dans la page pour
suivre les variables CSS. La silhouette n'est pas dessinée à la main : c'est le
contour extérieur des communes de `data/K4voge_*.geojson`, obtenu sans
dépendance en ne gardant que les arêtes qui n'appartiennent qu'à une seule
commune, puis simplifié (Douglas-Peucker, celui de `simplifier_geojson.py`).
Les lacs, qui ne sont pas des communes, en ressortent en trous.

    python maquette/logo.py            # imprime le <path> à coller dans la page
"""

import json
import math
import sys
from collections import defaultdict
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
from simplifier_geojson import douglas_peucker  # noqa: E402

LARGEUR = 100          # unités de la viewBox
TOLERANCE = 0.3        # en unités de viewBox : invisible à 80 px de large
TROU_MINIMUM = 0.004   # fraction de l'aire du pays : on garde les grands lacs


def _anneaux(geometrie):
    polygones = geometrie["coordinates"]
    if geometrie["type"] == "Polygon":
        polygones = [polygones]
    for polygone in polygones:
        yield from polygone


def contour(entrees, decimales=7):
    """Les anneaux formés par les arêtes qui ne bordent qu'une seule commune."""
    compte = defaultdict(int)
    for entree in entrees:
        for anneau in _anneaux(entree["geometry"]):
            points = [(round(x, decimales), round(y, decimales)) for x, y in anneau]
            for a, b in zip(points, points[1:]):
                if a != b:
                    compte[(a, b) if a < b else (b, a)] += 1
    bord = [arete for arete, n in compte.items() if n == 1]
    voisins = defaultdict(list)
    for a, b in bord:
        voisins[a].append(b)
        voisins[b].append(a)
    vues, anneaux = set(), []
    for depart, suivant in bord:
        if (depart, suivant) in vues:
            continue
        anneau, courant = [depart, suivant], suivant
        vues.update({(depart, suivant), (suivant, depart)})
        while courant != depart:
            prochain = next((c for c in voisins[courant] if (courant, c) not in vues), None)
            if prochain is None:
                break
            vues.update({(courant, prochain), (prochain, courant)})
            anneau.append(prochain)
            courant = prochain
        anneaux.append(anneau)
    return anneaux


def _aire(points):
    return sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(points, points[1:] + points[:1])) / 2


def projeter(anneaux):
    """Plate carrée corrigée en latitude, puis mise à l'échelle de la viewBox."""
    k = math.cos(math.radians(46.8))
    plats = [[(x * k, -y) for x, y in a] for a in anneaux]
    xs = [x for a in plats for x, _ in a]
    ys = [y for a in plats for _, y in a]
    x0, y0, echelle = min(xs), min(ys), LARGEUR / (max(xs) - min(xs))
    hauteur = (max(ys) - y0) * echelle
    return [[((x - x0) * echelle, (y - y0) * echelle) for x, y in a] for a in plats], hauteur


def chemin(anneaux, tolerance=TOLERANCE):
    morceaux = []
    for anneau in anneaux:
        simple = douglas_peucker(anneau, tolerance)
        if len(simple) < 4:
            continue
        morceaux.append("M" + " ".join(f"{x:.1f},{y:.1f}" for x, y in simple[:-1]) + "Z")
    return "".join(morceaux)


def construire(source):
    entrees = json.loads(Path(source).read_text())["features"]
    anneaux = [a for a in contour(entrees) if a[0] == a[-1]]
    plats, hauteur = projeter(anneaux)
    plats.sort(key=lambda a: -abs(_aire(a)))
    pays = abs(_aire(plats[0]))
    gardes = [plats[0]] + [a for a in plats[1:] if abs(_aire(a)) >= TROU_MINIMUM * pays]
    return chemin(gardes), hauteur, len(anneaux), len(gardes)


if __name__ == "__main__":
    source = sys.argv[1] if len(sys.argv) > 1 else ICI.parent / "data" / "K4voge_20220501_gf.geojson"
    d, hauteur, total, gardes = construire(source)
    print(f"<!-- viewBox=\"0 0 {LARGEUR} {hauteur:.1f}\" · {total} anneaux trouvés, {gardes} gardés, "
          f"{d.count(',')} points -->", file=sys.stderr)
    print(f'<path fill-rule="evenodd" d="{d}"/>')
