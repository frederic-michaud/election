"""Détection des communes nouvellement dépouillées (`update_scrutin_en_cours`).

La boucle ne portait que sur les deux premiers objets du scrutin : un scrutin
à un seul objet plantait, un scrutin à trois objets en ignorait un.
"""

from scrutin.management.commands.update_scrutin_en_cours import get_new_commune


def test_un_seul_objet_de_votation(tmp_path, ecrire_scrutin):
    """Un scrutin à un seul objet levait `IndexError`."""
    avant = ecrire_scrutin(tmp_path / "avant.json", [{1: False, 2: True}])
    apres = ecrire_scrutin(tmp_path / "apres.json", [{1: True, 2: True}])

    assert get_new_commune(str(avant), str(apres)) == {1}


def test_trois_objets_exigent_le_depouillement_de_chacun(tmp_path, ecrire_scrutin):
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


def test_aucune_nouvelle_commune(tmp_path, ecrire_scrutin):
    avant = ecrire_scrutin(tmp_path / "avant.json", [{1: True}, {1: True}])
    apres = ecrire_scrutin(tmp_path / "apres.json", [{1: True}, {1: True}])

    assert get_new_commune(str(avant), str(apres)) == set()
