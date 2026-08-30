import json

from scrutin.models import Commune, ResultatCommunalEnCours, SujetVote


def clean_date(date_str):
    return f'{date_str[0:4]}-{date_str[4:6]}-{date_str[6:8]}'

def communes_depouillees(sujet_json):
    return {
        data_commune['geoLevelnummer']
        for data_canton in sujet_json['kantone']
        for data_commune in data_canton['gemeinden']
        if data_commune['resultat']["jaStimmenAbsolut"] is not None
    }

def get_new_commune(path_previous, path_current):
    """Communes nouvellement dépouillées pour *tous* les objets du scrutin.

    On n'importe une commune que lorsqu'elle est rentrée pour chaque objet :
    la boucle ne portait que sur les deux premiers, et un scrutin peut en
    compter 1, 3 ou 4.
    """
    with open(path_previous, 'r') as f:
        data_old = json.load(f)
    with open(path_current, 'r') as f:
        data_new = json.load(f)
    nouvelles = None
    for sujet_ancien, sujet_nouveau in zip(data_old['schweiz']['vorlagen'],
                                           data_new['schweiz']['vorlagen']):
        nouvelles_du_sujet = (communes_depouillees(sujet_nouveau)
                              - communes_depouillees(sujet_ancien))
        if nouvelles is None:
            nouvelles = nouvelles_du_sujet
        else:
            nouvelles &= nouvelles_du_sujet
    return nouvelles if nouvelles is not None else set()
def import_votation(path_votation, commune_to_import):
    with open(path_votation, 'r') as f:
        data = json.load(f)
    for sujet_vote in data['schweiz']['vorlagen']:
        sujets = SujetVote.objects.filter(sujet_id = sujet_vote['vorlagenId'])
        if len(sujets) == 1:
            sujet = sujets[0]
        elif len(sujets) == 0:
            sujet = SujetVote(nom = sujet_vote['vorlagenTitel'][1]['text'],
                              sujet_id =  sujet_vote['vorlagenId'],
                              date = clean_date(data['abstimmtag']))
        else:
            raise Exception(f'There is more than one subject with id {sujet_vote["vorlagenId"]}')
        sujet.save()
        for data_canton in sujet_vote['kantone']:
            for data_commune in data_canton['gemeinden']:
                if data_commune['geoLevelnummer'] not in commune_to_import:
                    continue
                try:
                    commune = Commune.get_unique_commune_by_ofs(data_commune['geoLevelnummer'])
                except Exception:
                    print(f'Commune not found: {data_commune["geoLevelnummer"]}: {data_commune["geoLevelname"]}')
                    continue
                if (commune.nom in ['Rüti bei Lyssach', 'Jaberg']):
                    continue
                result = data_commune['resultat']
                ResultatCommunalEnCours.objects.update_or_create(
                    commune=commune,
                    sujet_vote=sujet,
                    defaults={
                        "electeur_election_precedente": commune.nb_voix,
                        "nombre_oui": result["jaStimmenAbsolut"],
                        "nombre_non": result["neinStimmenAbsolut"],
                        "electeurs_inscrits": result["anzahlStimmberechtigte"],
                        "bulletins_rentres": result["eingelegteStimmzettel"],
                        "comptabilise": True,
                    },
                )

def run(*args):
    if len(args) < 2:
        raise SystemExit("usage: runscript update_scrutin_en_cours "
                         "--script-args <json_precedent> <json_courant>")
    commune_to_import = get_new_commune(args[0], args[1])
    print(commune_to_import)
    import_votation(args[1], commune_to_import)
