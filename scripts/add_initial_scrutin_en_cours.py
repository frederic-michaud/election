import json

from scrutin.models import Commune, ResultatCommunalEnCours, SujetVote


def clean_date(date_str):
    return f'{date_str[0:4]}-{date_str[4:6]}-{date_str[6:8]}'

def import_votation(path_votation):
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
                try:
                    commune = Commune.get_unique_commune_by_ofs(data_commune['geoLevelnummer'])
                except Exception:
                    print(f'Commune not found: {data_commune["geoLevelnummer"]}: {data_commune["geoLevelname"]}')
                    continue
                if (commune.nom in ['Rüti bei Lyssach', 'Jaberg']):
                    continue
                scrutin = ResultatCommunalEnCours(commune=commune,
                                         electeur_election_precedente=commune.nb_voix,
                                         sujet_vote=sujet)
                scrutin.save()

def run(*args):
    if not args:
        raise SystemExit("usage: runscript add_initial_scrutin_en_cours "
                         "--script-args <json_du_scrutin>")
    ResultatCommunalEnCours.objects.all().delete()
    import_votation(args[0])
