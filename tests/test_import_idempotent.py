"""Les imports du jour J doivent être relançables sans créer de doublons.

`add_initial_scrutin_en_cours` crée une ligne `ResultatCommunalEnCours` vide par commune
et par objet ; `update_scrutin_en_cours` doit **remplir celle-là**, pas en
ajouter une seconde. Sinon une commune dépouillée existe en double — une ligne
comptabilisée et une ligne vide — et l'extrapolation la compte deux fois : une
fois pour de vrai, une fois comme commune à estimer.
"""

import datetime
import json

import pytest
from django.db.utils import IntegrityError

from scrutin.management.commands.add_initial_scrutin_en_cours import (
    import_votation as import_initial,
)
from scrutin.management.commands.update_scrutin_en_cours import (
    import_votation as import_mise_a_jour,
)
from scrutin.models import Canton, Commune, District, ResultatCommunalEnCours, SujetVote

OFS = [1001, 1002, 1003]


@pytest.fixture
def communes(db):
    canton = Canton.objects.create(nom="Vaud", abreviation="VD")
    district = District.objects.create(nom="Lavaux-Oron", numero_ofs=1, canton=canton)
    return [
        Commune.objects.create(nom=f"Commune {ofs}", numero_ofs=ofs,
                               canton=canton, district=district, nb_voix=2000)
        for ofs in OFS
    ]


def ecrire_scrutin(chemin, depouillees=()):
    data = {
        "abstimmtag": "20260927",
        "schweiz": {"vorlagen": [{
            "vorlagenId": 1,
            "vorlagenTitel": [{"text": "Vorlage"}, {"text": "Objet de test"}],
            "kantone": [{"gemeinden": [
                {
                    "geoLevelnummer": ofs,
                    "geoLevelname": f"Commune {ofs}",
                    "resultat": {
                        "jaStimmenAbsolut": 600 if ofs in depouillees else None,
                        "neinStimmenAbsolut": 400 if ofs in depouillees else None,
                        "anzahlStimmberechtigte": 2000 if ofs in depouillees else None,
                        "eingelegteStimmzettel": 1000 if ofs in depouillees else None,
                    },
                }
                for ofs in OFS
            ]}],
        }]},
    }
    chemin.write_text(json.dumps(data))
    return str(chemin)


def test_la_mise_a_jour_remplit_la_ligne_existante(communes, tmp_path):
    import_initial(ecrire_scrutin(tmp_path / "initial.json"))
    assert ResultatCommunalEnCours.objects.count() == len(OFS)

    import_mise_a_jour(ecrire_scrutin(tmp_path / "t1.json", depouillees=[1001]),
                       commune_to_import={1001})

    assert ResultatCommunalEnCours.objects.count() == len(OFS), (
        "la commune dépouillée existe en double : une ligne comptabilisée et "
        "une ligne vide, que l'extrapolation compterait toutes les deux"
    )
    ligne = ResultatCommunalEnCours.objects.get(commune__numero_ofs=1001)
    assert ligne.comptabilise is True
    assert (ligne.nombre_oui, ligne.nombre_non) == (600, 400)


def test_rejouer_le_meme_json_ne_cree_pas_de_doublon(communes, tmp_path):
    import_initial(ecrire_scrutin(tmp_path / "initial.json"))
    courant = ecrire_scrutin(tmp_path / "t1.json", depouillees=[1001, 1002])

    import_mise_a_jour(courant, commune_to_import={1001, 1002})
    import_mise_a_jour(courant, commune_to_import={1001, 1002})

    assert ResultatCommunalEnCours.objects.count() == len(OFS)
    assert ResultatCommunalEnCours.objects.filter(comptabilise=True).count() == 2


def test_l_import_initial_est_relancable(communes, tmp_path):
    initial = ecrire_scrutin(tmp_path / "initial.json")

    import_initial(initial)
    import_initial(initial)

    assert ResultatCommunalEnCours.objects.count() == len(OFS)


def test_une_commune_absente_de_la_base_est_ignoree(communes, tmp_path):
    """Le JSON fédéral contient des communes que la base ne connaît pas."""
    Commune.objects.filter(numero_ofs=1003).delete()

    import_initial(ecrire_scrutin(tmp_path / "initial.json"))

    assert ResultatCommunalEnCours.objects.count() == len(OFS) - 1


def test_la_date_du_sujet_vient_du_json(communes, tmp_path):
    import_initial(ecrire_scrutin(tmp_path / "initial.json"))

    ligne = ResultatCommunalEnCours.objects.first()
    assert ligne.sujet_vote.date == datetime.date(2026, 9, 27)


@pytest.mark.django_db
def test_la_base_refuse_desormais_un_doublon(communes):
    """L'invariant n'était tenu que par le code ; il l'est maintenant par la base."""
    sujet = SujetVote.objects.create(nom="Objet", sujet_id=8000,
                                     date=datetime.date(2026, 9, 27))
    commune = Commune.objects.first()
    ResultatCommunalEnCours.objects.create(commune=commune, sujet_vote=sujet,
                                           electeur_election_precedente=10)

    with pytest.raises(IntegrityError):
        ResultatCommunalEnCours.objects.create(commune=commune, sujet_vote=sujet,
                                               electeur_election_precedente=10)
