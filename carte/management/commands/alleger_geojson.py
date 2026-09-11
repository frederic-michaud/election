"""Fabrique ``carte/static/carte/communes.geojson`` à partir du GeoJSON source.

À relancer quand la source est mise à jour, puis committer le résultat.
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand

SOURCE = Path("data/K4voge_20220501_gf.geojson")
CIBLE = Path("carte/static/carte/communes.geojson")
DECIMALES = 5


def arrondir(coordonnees):
    if isinstance(coordonnees[0], (int, float)):
        return [round(x, DECIMALES) for x in coordonnees]
    return [arrondir(c) for c in coordonnees]


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument("source", nargs="?", default=SOURCE, type=Path)
        parser.add_argument("cible", nargs="?", default=CIBLE, type=Path)

    def handle(self, source, cible, **options):
        with open(source) as f:
            gj = json.load(f)
        features = [{
            "type": "Feature",
            "properties": {"vogeId": f["properties"]["vogeId"], "vogeName": f["properties"]["vogeName"]},
            "geometry": {"type": f["geometry"]["type"], "coordinates": arrondir(f["geometry"]["coordinates"])},
        } for f in gj["features"]]
        cible.parent.mkdir(parents=True, exist_ok=True)
        with open(cible, "w") as f:
            json.dump({"type": "FeatureCollection", "features": features}, f, separators=(",", ":"))
        self.stdout.write(f"{len(features)} communes → {cible} ({cible.stat().st_size // 1000} ko)")
