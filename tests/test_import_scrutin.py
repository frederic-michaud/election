"""Détection des communes nouvellement dépouillées (`update_scrutin_en_cours`).

La boucle ne portait que sur les deux premiers objets du scrutin : un scrutin
à un seul objet plantait, un scrutin à trois objets en ignorait un.
"""

import json

from scrutin.management.commands.update_scrutin_en_cours import get_new_commune


def ecrire_scrutin(chemin, objets):
    """Fabrique un JSON fédéral minimal.

    ``objets`` est une liste (un élément par objet de votation) de dicts
    ``{numero_ofs: dépouillée ou non}``.
    """
    data = {"schweiz": {"vorlagen": [
        {
            "vorlagenId": index + 1,
            "kantone": [{"gemeinden": [
                {
                    "geoLevelnummer": ofs,
                    "geoLevelname": f"Commune {ofs}",
                    "resultat": {"jaStimmenAbsolut": 100 if depouillee else None},
                }
                for ofs, depouillee in communes.items()
            ]}],
        }
        for index, communes in enumerate(objets)
    ]}}
    chemin.write_text(json.dumps(data))
    return chemin


def test_un_seul_objet_de_votation(tmp_path):
    """Un scrutin à un seul objet levait `IndexError`."""
    avant = ecrire_scrutin(tmp_path / "avant.json", [{1: False, 2: True}])
    apres = ecrire_scrutin(tmp_path / "apres.json", [{1: True, 2: True}])

    assert get_new_commune(str(avant), str(apres)) == {1}


def test_trois_objets_exigent_le_depouillement_de_chacun(tmp_path):
    """Le troisième objet était ignoré : une commune incomplète passait."""
    avant = ecrire_scrutin(tmp_path / "avant.json", [
        {1: False, 2: False},
        {1: False, 2: False},
        {1: False, 2: False},
    ])
    apres = ecrire_scrutin(tmp_path / "apres.json", [
        {1: True, 2: True},
        {1: True, 2: True},
        # La commune 2 n'est pas rentrée pour le troisième objet.
        {1: True, 2: False},
    ])

    assert get_new_commune(str(avant), str(apres)) == {1}


def test_aucune_nouvelle_commune(tmp_path):
    avant = ecrire_scrutin(tmp_path / "avant.json", [{1: True}, {1: True}])
    apres = ecrire_scrutin(tmp_path / "apres.json", [{1: True}, {1: True}])

    assert get_new_commune(str(avant), str(apres)) == set()
