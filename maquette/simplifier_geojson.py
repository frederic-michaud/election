"""Allège le GeoJSON communal pour la maquette, sans dépendance.

1,6 Mo de contours recopiés dans chaque carte, c'est ce qui rend la page
lourde — sur la maquette comme sur le site.

Deux leviers, et le second pèse bien plus lourd que le premier :

- **Douglas-Peucker** sur les contours. Gain modeste ici : le fichier de l'OFS
  est déjà généralisé (≈ 13 points par commune).
- **Arrondi des coordonnées.** Elles sont stockées avec 16 décimales, soit le
  milliardième de millimètre. Quatre décimales (≈ 10 m) suffisent largement
  pour une carte du pays et divisent le fichier par trois.

Ne remplace pas `data/K4voge_*.geojson` : écrit une copie dans `maquette/`.
"""

import json
from pathlib import Path


def _perpendiculaire(point, debut, fin):
    (x, y), (x1, y1), (x2, y2) = point, debut, fin
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return ((x - x1) ** 2 + (y - y1) ** 2) ** 0.5
    return abs(dy * x - dx * y + x2 * y1 - y2 * x1) / (dx * dx + dy * dy) ** 0.5


def douglas_peucker(points, tolerance):
    if len(points) < 3:
        return points
    pire, index = 0.0, 0
    for i in range(1, len(points) - 1):
        distance = _perpendiculaire(points[i], points[0], points[-1])
        if distance > pire:
            pire, index = distance, i
    if pire <= tolerance:
        return [points[0], points[-1]]
    gauche = douglas_peucker(points[:index + 1], tolerance)
    droite = douglas_peucker(points[index:], tolerance)
    return gauche[:-1] + droite


def _arrondir(points, decimales):
    """Arrondit, puis retire les points devenus identiques à leur voisin."""
    arrondis = [(round(x, decimales), round(y, decimales)) for x, y in points]
    garde = [arrondis[0]]
    for point in arrondis[1:]:
        if point != garde[-1]:
            garde.append(point)
    return garde


def _anneau(points, tolerance, decimales):
    """Un anneau fermé reste fermé, et garde au moins un triangle."""
    simplifie = _arrondir(douglas_peucker(points, tolerance), decimales)
    if len(simplifie) < 4:
        return points if len(points) >= 4 else None
    if simplifie[0] != simplifie[-1]:
        simplifie.append(simplifie[0])
    return simplifie


def _geometrie(geometrie, tolerance, decimales):
    if geometrie["type"] == "Polygon":
        anneaux = [_anneau(a, tolerance, decimales) for a in geometrie["coordinates"]]
        anneaux = [a for a in anneaux if a]
        return {"type": "Polygon", "coordinates": anneaux} if anneaux else None
    if geometrie["type"] == "MultiPolygon":
        polygones = []
        for polygone in geometrie["coordinates"]:
            anneaux = [_anneau(a, tolerance, decimales) for a in polygone]
            anneaux = [a for a in anneaux if a]
            if anneaux:
                polygones.append(anneaux)
        return {"type": "MultiPolygon", "coordinates": polygones} if polygones else None
    return geometrie


def compter(gj):
    total = 0
    for entree in gj["features"]:
        pile = [entree["geometry"]["coordinates"]]
        while pile:
            element = pile.pop()
            if element and isinstance(element[0][0], (int, float)):
                total += len(element)
            else:
                pile.extend(element)
    return total


def simplifier(source, destination, tolerance=0.0008, decimales=4):
    gj = json.loads(Path(source).read_text())
    avant = compter(gj)
    gardees = []
    for entree in gj["features"]:
        geometrie = _geometrie(entree["geometry"], tolerance, decimales)
        if geometrie is not None:
            gardees.append({"type": "Feature",
                            "properties": entree["properties"],
                            "geometry": geometrie})
    gj["features"] = gardees
    Path(destination).write_text(json.dumps(gj, separators=(",", ":")))
    apres = compter(gj)
    return avant, apres


if __name__ == "__main__":
    import sys
    ici = Path(__file__).resolve().parent
    source = sys.argv[1] if len(sys.argv) > 1 else ici.parent / "data" / "K4voge_20220501_gf.geojson"
    destination = ici / "communes-simplifie.geojson"
    avant, apres = simplifier(source, destination)
    print(f"{avant} → {apres} points ({100 * apres / avant:.0f} %), "
          f"{Path(source).stat().st_size / 1e6:.1f} → {destination.stat().st_size / 1e6:.1f} Mo")
