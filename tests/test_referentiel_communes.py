"""Import du référentiel officiel des communes (API AGVCH de l'OFS).

`populate_commune` et `import_metadata_commune` lisaient deux CSV hors dépôt,
dans `../data/communes/`, dont personne ne connaissait plus la provenance.
Elles lisent maintenant les exports de l'API AGVCH versionnés dans `data/`.

Le CSV réduit ci-dessous est fait de **vraies lignes** du répertoire au
01.01.2026, choisies pour les cas qui piègent :

- `Bezirk Affoltern` (district) et `Steinmaur` (commune) portent le même
  `BfsCode` 101 : le code OFS n'est unique qu'à l'intérieur d'un niveau ;
- `Wahlkreis Wil` (district) et `Wil (ZH)` (commune) portent le même
  `HistoricalCode` 10268 : celui-ci non plus n'est unique qu'au sein d'un
  niveau, alors que c'est lui qui chaîne la hiérarchie via `Parent` ;
- `Kanton Uri` est une ligne de niveau 2 qui couvre un canton entier — neuf
  cantons n'ont pas de districts et sont dans ce cas.
"""

import pytest
from django.core.management import call_command

from scrutin.models import Canton, Commune, District

SNAPSHOT = """\
HistoricalCode,BfsCode,ValidFrom,ValidTo,Level,Parent,Name,ShortName,Inscription,Radiation,Rec_Type_fr,Rec_Type_de
1,1,12.09.1848,,1,,Zürich,ZH,,,,
4,4,12.09.1848,,1,,Uri,UR,,,,
10,10,12.09.1848,,1,,Fribourg / Freiburg,FR,,,,
17,17,12.09.1848,,1,,St. Gallen,SG,,,,
18,18,12.09.1848,,1,,Graubünden / Grigioni / Grischun,GR,,,,
21,21,12.09.1848,,1,,Ticino,TI,,,,
23,23,12.09.1848,,1,,Valais / Wallis,VS,,,,
10053,101,12.09.1848,,2,1,Bezirk Affoltern,Affoltern,100,,,
10080,104,12.09.1848,,2,1,Bezirk Dielsdorf,Dielsdorf,100,,,
10081,103,12.09.1848,,2,1,Bezirk Bülach,Bülach,100,,,
10061,400,12.09.1848,,2,4,Kanton Uri,Kt. Uri,100,,Canton qui n’est pas subdivisé en districts,Kanton ohne Bezirksunterteilung
10104,1004,12.09.1848,,2,10,District de la Sarine,La Sarine,100,,,
10268,1728,01.01.2003,,2,17,Wahlkreis Wil,Wil,149,,,
10316,1850,01.01.2017,,2,18,Region Surselva,Surselva,155,,,
10002,2106,12.09.1848,,2,21,Distretto di Mendrisio,Mendrisio,100,,,
10013,2308,12.09.1848,,2,23,District de Monthey,Monthey,100,,,
10597,101,12.09.1848,,3,10080,Steinmaur,Steinmaur,,,,
10268,71,12.09.1848,,3,10081,Wil (ZH),Wil (ZH),,,,
15610,3427,01.01.2003,,3,10268,Wil (SG),Wil (SG),,,,
10364,1218,12.09.1848,,3,10061,Spiringen,Spiringen,,,,
10162,2228,12.09.1848,,3,10104,Villars-sur-Glâne,Villars-sur-Glâne,,,,
15969,3572,01.01.2017,,3,10316,Falera,Falera,3533,,,
10381,5266,12.09.1848,,3,10002,Stabio,Stabio,,,,
10078,6158,12.09.1848,,3,10013,Vionnaz,Vionnaz,,,,
"""

# L'export `levels` porte 29 colonnes ; seules ces quatre-là sont lues.
# Valeurs réelles elles aussi : Falera est la commune romanche, Stabio
# l'italienne, Villars-sur-Glâne la seule urbaine du lot.
NIVEAUX = """\
HistoricalCode,BfsCode,Name,DEGURB2021,SPRGEB2020
10597,101,Steinmaur,2,1
10268,71,Wil (ZH),3,1
15610,3427,Wil (SG),2,1
10364,1218,Spiringen,3,1
10162,2228,Villars-sur-Glâne,1,2
15969,3572,Falera,3,4
10381,5266,Stabio,2,3
10078,6158,Vionnaz,3,2
"""

REEL_SNAPSHOT = "data/agvch_communes_2026-01-01.csv"
REEL_NIVEAUX = "data/agvch_niveaux_2026-01-01.csv"


@pytest.fixture
def snapshot(tmp_path):
    chemin = tmp_path / "snapshot.csv"
    chemin.write_text(SNAPSHOT, encoding="utf-8")
    return str(chemin)


@pytest.fixture
def niveaux(tmp_path):
    chemin = tmp_path / "niveaux.csv"
    chemin.write_text(NIVEAUX, encoding="utf-8")
    return str(chemin)


@pytest.mark.django_db
def test_les_trois_niveaux_sont_importes(snapshot):
    call_command("populate_commune", snapshot)

    assert Canton.objects.count() == 7
    assert District.objects.count() == 9
    assert Commune.objects.count() == 8


@pytest.mark.django_db
def test_hierarchie_chainee_par_historical_code_et_non_par_bfs_code(snapshot):
    """`Steinmaur` porte le BfsCode 101, celui du `Bezirk Affoltern`.

    Chaîner par BfsCode la rattacherait au mauvais district.
    """
    call_command("populate_commune", snapshot)

    steinmaur = Commune.get_unique_commune_by_ofs(101)
    assert steinmaur.district.nom == "Bezirk Dielsdorf"
    assert steinmaur.canton.abreviation == "ZH"


@pytest.mark.django_db
def test_historical_code_partage_entre_un_district_et_une_commune(snapshot):
    """10268 désigne à la fois `Wahlkreis Wil` et la commune `Wil (ZH)`.

    Le `Parent` d'une commune se résout parmi les seules lignes de niveau 2 :
    un dictionnaire global renverrait ici une commune comme district.
    """
    call_command("populate_commune", snapshot)

    wil_sg = Commune.get_unique_commune_by_ofs(3427)
    assert wil_sg.district.nom == "Wahlkreis Wil"
    assert wil_sg.canton.abreviation == "SG"

    wil_zh = Commune.get_unique_commune_by_ofs(71)
    assert wil_zh.district.nom == "Bezirk Bülach"
    assert wil_zh.canton.abreviation == "ZH"


@pytest.mark.django_db
def test_canton_sans_districts(snapshot):
    """Uri n'est pas subdivisé : sa ligne de niveau 2 couvre le canton entier."""
    call_command("populate_commune", snapshot)

    spiringen = Commune.get_unique_commune_by_ofs(1218)
    assert spiringen.district.nom == "Kanton Uri"
    assert spiringen.district.numero_ofs == 400
    assert spiringen.canton.abreviation == "UR"


@pytest.mark.django_db
def test_les_cantons_gardent_leurs_noms_francais(snapshot):
    """AGVCH nomme les cantons dans leurs langues officielles ; le site est
    francophone, et `peupler_demo` sème déjà ces noms-là."""
    call_command("populate_commune", snapshot)

    assert Canton.get_unique_canton_by_abreviation("GR").nom == "Grisons"
    assert Canton.get_unique_canton_by_abreviation("VS").nom == "Valais"


@pytest.mark.django_db
def test_reimport_ne_duplique_rien(snapshot):
    """La commande repart d'une table vide : elle est rejouable."""
    call_command("populate_commune", snapshot)
    call_command("populate_commune", snapshot)

    assert Canton.objects.count() == 7
    assert District.objects.count() == 9
    assert Commune.objects.count() == 8


@pytest.mark.django_db
def test_langue_et_urbanisation_traduites(snapshot, niveaux):
    """Les codes numériques de l'OFS deviennent les étiquettes du site."""
    call_command("populate_commune", snapshot)
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
def test_commune_absente_de_la_base_est_ignoree(snapshot, niveaux, tmp_path, caplog):
    """Une commune du fichier `levels` sans ligne en base ne fait pas tout échouer."""
    call_command("populate_commune", snapshot)
    inconnue = tmp_path / "niveaux_inconnue.csv"
    inconnue.write_text(NIVEAUX + "99999,9999,Commune inconnue,1,1\n", encoding="utf-8")

    call_command("import_metadata_commune", str(inconnue))

    assert "9999" in caplog.text
    assert Commune.get_unique_commune_by_ofs(5266).langue == "italien"


@pytest.mark.lent
@pytest.mark.django_db
def test_le_repertoire_versionne_couvre_toute_la_suisse():
    """Garde-fou sur les fichiers réellement commités dans `data/`.

    Ce sont les valeurs par défaut des deux commandes : si l'un des deux
    fichiers disparaît ou change de forme, c'est ici que ça se voit.
    """
    call_command("populate_commune", REEL_SNAPSHOT)
    call_command("import_metadata_commune", REEL_NIVEAUX)

    assert Canton.objects.count() == 26
    assert District.objects.count() == 144
    assert Commune.objects.count() == 2110
    assert not Commune.objects.filter(langue__isnull=True).exists()
    assert not Commune.objects.filter(degre_urbanisation__isnull=True).exists()
