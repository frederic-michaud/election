"""La carte des axes de l'ACP : un axe affiché, les six dans la page."""

import json

import pytest

from carte.API import contours, figure_carte_acp


def test_la_carte_porte_les_six_axes_et_leur_echelle():
    # Vingt communes du GeoJSON : le premier axe vaut 0, 1, … 19, les autres sont nuls.
    communes = [f["properties"]["vogeId"] for f in contours()[0]["features"]][:20]
    profils = {ofs: [float(rang), 0, 0, 0, 0, 0] for rang, ofs in enumerate(communes)}
    figure = figure_carte_acp(profils)
    axes = figure.layout.meta["axes"]
    assert [axe["nom"] for axe in axes] == [f"Axe {i}" for i in range(1, 7)]
    assert figure.data[0].z == tuple(axes[0]["valeurs"])
    assert axes[0]["survol"][1] == "Axe 1 : +1,00"
    # Échelle symétrique autour de zéro, bornée au 95ᵉ centile et non au maximum.
    axe_couleur = figure.layout.coloraxis
    assert (axe_couleur.cmin, axe_couleur.cmid, axe_couleur.cmax) == (-18.0, 0, 18.0)


@pytest.mark.lent
@pytest.mark.django_db
def test_la_page_de_la_carte_acp(base_demo, client):
    html = client.get("/cartes-acp").content.decode()
    assert '<option value="5">Axe 6</option>' in html
    assert "tracerCarteACP();" in html
    figure = json.loads(html.split('<script type="application/json">')[1].split("</script>")[0])
    axes = figure["layout"]["meta"]["axes"]
    assert len(axes) == 6 and len(axes[0]["valeurs"]) > 2000
