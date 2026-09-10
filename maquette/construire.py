"""Fabrique les données de la maquette statique depuis la base fictive.

    python manage.py peupler_demo      # une fois
    python maquette/construire.py      # puis ouvrir maquette/accueil.html

Écrit ``figures.js`` (le contrat de vue et les figures Plotly en JSON),
allège le GeoJSON communal et copie ``plotly.min.js`` depuis le paquet
Python — la même version que celle qui produit les figures. Ces fichiers sont
générés, jamais édités à la main, et ne sont pas versionnés.

Les cartes sont exportées dans **les deux variantes** (Mapbox comme le site
aujourd'hui, et projection SVG sans WebGL) : les maquettes peuvent les
comparer côte à côte, ce que la Partie 7.2 doit trancher.

Les figures sortent **des mêmes fonctions que le site** (``figure_histogramme``,
``figure_carte``) : la maquette ne peut pas promettre un rendu que Django ne
donnerait pas. Ce que la maquette ajoute par-dessus vit dans ``charte.js``.

Un ``<script src>`` local fonctionne en ``file://``, un ``fetch`` non : c'est
pourquoi on écrit du JS (``window.FIGURES = …``) et pas du JSON.

Le GeoJSON est **sorti des figures et écrit une seule fois**
(``window.GEOJSON``) : Plotly le recopie dans chaque trace, ce qui pesait
six fois le même mégaoctet. ``charte.js`` le rebranche au chargement.
"""

import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

ICI = Path(__file__).resolve().parent
RACINE = ICI.parent
sys.path.insert(0, str(RACINE))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "election.settings")

import django  # noqa: E402

django.setup()

import plotly  # noqa: E402
import plotly.io as pio  # noqa: E402

from carte.API import figure_carte, figure_carte_svg  # noqa: E402
from maquette.simplifier_geojson import simplifier  # noqa: E402
from scrutin.donnees import construire_vue_accueil  # noqa: E402
from scrutin.graphiques import figure_histogramme  # noqa: E402


def sans_geojson(figure):
    """Le JSON de la figure, contours retirés (``charte.js`` les rebranche)."""
    brut = json.loads(pio.to_json(figure))
    for trace in brut["data"]:
        trace.pop("geojson", None)
    return json.dumps(brut, separators=(",", ":"))


def main():
    vue = construire_vue_accueil()

    geojson_leger = ICI / "communes-simplifie.geojson"
    avant, apres = simplifier(RACINE / "data" / "K4voge_20220501_gf.geojson", geojson_leger)

    # Le contrat sans les résultats par commune : ils sont déjà dans les cartes.
    vue_legere = {
        "date": vue["date"],
        "avance": vue["avance"],
        "sujets": [{k: v for k, v in sujet.items() if k != "communes"} for sujet in vue["sujets"]],
    }

    morceaux = ["// Généré par maquette/construire.py — ne pas éditer.\n"]
    morceaux.append(f"window.VUE = {pio.json.to_json_plotly(vue_legere)};\n")
    morceaux.append("window.FIGURES = {\n")
    morceaux.append(f"  histogramme: {pio.to_json(figure_histogramme(vue))},\n")
    for cle, fabrique in (("cartes", figure_carte), ("cartes_svg", figure_carte_svg)):
        morceaux.append(f"  {cle}: {{\n")
        for sujet in vue["sujets"]:
            figure = fabrique(sujet["communes"], chemin_geojson=geojson_leger)
            morceaux.append(f"    {sujet['id']}: {sans_geojson(figure)},\n")
        morceaux.append("  },\n")
    morceaux.append("};\n")
    morceaux.append(f"window.GEOJSON = {geojson_leger.read_text()};\n")
    sortie = ICI / "figures.js"
    sortie.write_text("".join(morceaux), encoding="utf-8")

    source_js = Path(plotly.__file__).parent / "package_data" / "plotly.min.js"
    shutil.copyfile(source_js, ICI / "plotly.min.js")

    # Témoin léger : `index.html` le charge pour savoir si la maquette est
    # prête, sans avoir à tirer les 1,8 Mo de figures.js.
    (ICI / "pret.js").write_text(
        f'window.MAQUETTE_PRETE = "{datetime.now().strftime("%d.%m.%Y %H:%M")}";\n',
        encoding="utf-8")

    print(f"GeoJSON allégé : {avant} → {apres} points, "
          f"{geojson_leger.stat().st_size / 1e6:.1f} Mo\n"
          f"{sortie.name} : {sortie.stat().st_size / 1e6:.1f} Mo "
          f"({len(vue['sujets'])} objets × 2 variantes de carte)\n"
          f"plotly.min.js : {source_js.stat().st_size / 1e6:.1f} Mo "
          f"(Plotly {plotly.__version__})")


if __name__ == "__main__":
    main()
