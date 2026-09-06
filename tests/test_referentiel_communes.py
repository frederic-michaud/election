"""Import du référentiel officiel des communes (API AGVCH de l'OFS).

`populate_commune` et `import_metadata_commune` lisaient deux CSV hors dépôt,
dans `../data/communes/`, dont personne ne connaissait plus la provenance.
Elles lisent maintenant le **même** export de l'API AGVCH, versionné dans
`data/` : une ligne par commune, la hiérarchie déjà jointe.

Le CSV réduit ci-dessous est fait de **vraies lignes** du répertoire au
01.01.2026, choisies pour les cas qui comptent : deux communes d'un même
district, un canton sans districts (`Kanton Uri` est une entrée de district
qui couvre le canton entier — huit autres cantons sont dans ce cas), les
quatre langues et les trois degrés d'urbanisation. Le fichier réel porte 29
colonnes ; seules celles-ci sont lues.
"""

import pytest
from django.core.management import call_command

from scrutin.models import Canton, Commune, District

NIVEAUX = """\
HistoricalCode,BfsCode,Name,CantonId,Canton,DistrictId,District,DEGURB2021,SPRGEB2020
10597,101,Steinmaur,1,Zürich,10080,Bezirk Dielsdorf,2,1
12534,89,Niederglatt,1,Zürich,10080,Bezirk Dielsdorf,2,1
10268,71,Wil (ZH),1,Zürich,10081,Bezirk Bülach,3,1
15610,3427,Wil (SG),17,St. Gallen,10268,Wahlkreis Wil,2,1
10364,1218,Spiringen,4,Uri,10061,Kanton Uri,3,1
10162,2228,Villars-sur-Glâne,10,Fribourg / Freiburg,10104,District de la Sarine,1,2
15969,3572,Falera,18,Graubünden / Grigioni / Grischun,10316,Region Surselva,3,4
10381,5266,Stabio,21,Ticino,10002,Distretto di Mendrisio,2,3
10078,6158,Vionnaz,23,Valais / Wallis,10013,District de Monthey,3,2
"""

REEL = "data/agvch_niveaux_2026-01-01.csv"


@pytest.fixture
def niveaux(tmp_path):
    chemin = tmp_path / "niveaux.csv"
    chemin.write_text(NIVEAUX, encoding="utf-8")
    return str(chemin)


@pytest.mark.django_db
def test_les_trois_niveaux_sont_importes(niveaux):
    """Un district partagé par deux communes n'est créé qu'une fois."""
    call_command("populate_commune", niveaux)

    assert Canton.objects.count() == 7
    assert District.objects.count() == 8
    assert Commune.objects.count() == 9


@pytest.mark.django_db
def test_chaque_commune_rejoint_son_district_et_son_canton(niveaux):
    call_command("populate_commune", niveaux)

    steinmaur = Commune.get_unique_commune_by_ofs(101)
    assert steinmaur.district.nom == "Bezirk Dielsdorf"
    assert steinmaur.canton.abreviation == "ZH"

    wil_sg = Commune.get_unique_commune_by_ofs(3427)
    assert wil_sg.district.nom == "Wahlkreis Wil"
    assert wil_sg.canton.abreviation == "SG"


@pytest.mark.django_db
def test_le_district_porte_le_code_historique_de_l_ofs(niveaux):
    """`levels` ne publie pas le numéro OFS du district, mais son `DistrictId`.

    Le champ s'appelle donc `code_historique` : il rattache les communes à leur
    district, rien de plus. Les résultats de votation sont rattachés à des
    communes, jamais à des districts.
    """
    call_command("populate_commune", niveaux)

    assert Commune.get_unique_commune_by_ofs(101).district.code_historique == 10080
    assert Commune.get_unique_commune_by_ofs(3427).district.code_historique == 10268


@pytest.mark.django_db
def test_canton_sans_districts(niveaux):
    """Uri n'est pas subdivisé : son entrée de district couvre le canton entier."""
    call_command("populate_commune", niveaux)

    spiringen = Commune.get_unique_commune_by_ofs(1218)
    assert spiringen.district.nom == "Kanton Uri"
    assert spiringen.canton.abreviation == "UR"


@pytest.mark.django_db
def test_les_cantons_gardent_leurs_noms_francais(niveaux):
    """AGVCH nomme les cantons dans toutes leurs langues officielles et ne
    donne pas d'abréviation ; le site est francophone, et `peupler_demo` sème
    déjà ces noms-là."""
    call_command("populate_commune", niveaux)

    assert Canton.get_unique_canton_by_abreviation("GR").nom == "Grisons"
    assert Canton.get_unique_canton_by_abreviation("VS").nom == "Valais"


@pytest.mark.django_db
def test_reimport_ne_duplique_rien(niveaux):
    """La commande repart d'une table vide : elle est rejouable."""
    call_command("populate_commune", niveaux)
    call_command("populate_commune", niveaux)

    assert Canton.objects.count() == 7
    assert District.objects.count() == 8
    assert Commune.objects.count() == 9


@pytest.mark.django_db
def test_langue_et_urbanisation_traduites(niveaux):
    """Les codes numériques de l'OFS deviennent les étiquettes du site."""
    call_command("populate_commune", niveaux)
    call_command("import_metadata_commune", niveaux)

    langues = {c.numero_ofs: c.langue for c in Commune.objects.all()}
    assert langues[101] == "allemand"
    assert langues[6158] == "français"
    assert langues[5266] == "italien"
    assert langues[3572] == "romanche"

    urbanisation = {c.numero_ofs: c.degre_urbanisation for c in Commune.objects.all()}
    assert urbanisation[2228] == "urbain"
    assert urbanisation[3427] == "intermédiaire"
    assert urbanisation[1218] == "rural"


@pytest.mark.django_db
def test_commune_absente_de_la_base_est_ignoree(niveaux, tmp_path, caplog):
    """Une commune du fichier sans ligne en base ne fait pas tout échouer.

    Le cas se produit dès que le référentiel avance d'un millésime sans que
    `populate_commune` soit rejoué.
    """
    call_command("populate_commune", niveaux)
    inconnue = tmp_path / "niveaux_inconnue.csv"
    inconnue.write_text(
        NIVEAUX + "99999,9999,Commune inconnue,1,Zürich,10080,Bezirk Dielsdorf,1,1\n",
        encoding="utf-8",
    )

    call_command("import_metadata_commune", str(inconnue))

    assert "9999" in caplog.text
    assert Commune.get_unique_commune_by_ofs(5266).langue == "italien"


@pytest.mark.lent
@pytest.mark.django_db
def test_le_repertoire_versionne_couvre_toute_la_suisse():
    """Garde-fou sur le fichier réellement commité dans `data/`.

    C'est la valeur par défaut des deux commandes : s'il disparaît ou change
    de forme, c'est ici que ça se voit.
    """
    call_command("populate_commune", REEL)
    call_command("import_metadata_commune", REEL)

    assert Canton.objects.count() == 26
    assert District.objects.count() == 144
    assert Commune.objects.count() == 2110
    assert not Commune.objects.filter(langue__isnull=True).exists()
    assert not Commune.objects.filter(degre_urbanisation__isnull=True).exists()
