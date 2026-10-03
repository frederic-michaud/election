"""Quelles communes `update_scrutin_en_cours` tient pour dépouillées."""

import json

from scrutin.management.commands.update_scrutin_en_cours import communes_depouillees


def premier_objet(chemin):
    return json.loads(chemin.read_text())["schweiz"]["vorlagen"][0]


def test_seul_gebiet_ausgezaehlt_compte(tmp_path, ecrire_scrutin):
    chemin = ecrire_scrutin(tmp_path / "t.json", [{1: True, 2: False}])

    assert communes_depouillees(premier_objet(chemin)) == {1}


def test_resultat_partiel_pas_encore_depouille(tmp_path, ecrire_scrutin):
    """Une grande ville publie des voix avant la fin de son dépouillement."""
    chemin = ecrire_scrutin(tmp_path / "t.json", [{1: False}])
    data = json.loads(chemin.read_text())
    data["schweiz"]["vorlagen"][0]["kantone"][0]["gemeinden"][0]["resultat"][
        "jaStimmenAbsolut"] = 4200
    chemin.write_text(json.dumps(data))

    assert communes_depouillees(premier_objet(chemin)) == set()
