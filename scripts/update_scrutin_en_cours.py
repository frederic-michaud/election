from scrutin.models import ScrutinEnCours, Commune, SujetVote
import json
import numpy as np

def clean_date(date_str):
    return f'{date_str[0:4]}-{date_str[4:6]}-{date_str[6:8]}'

def get_new_commune(path_previous, path_current):
    with open(path_previous, 'r') as f:
        data_old = json.load(f)
    with open(path_current, 'r') as f:
        data_new = json.load(f)
    commune_known_previous = []
    first_object = data_old['schweiz']['vorlagen'][0]
    for data_canton in first_object['kantone']:
        for data_commune in data_canton['gemeinden']:
            if data_commune['resultat']["jaStimmenAbsolut"] is not None:
                commune_known_previous.append(data_commune['geoLevelnummer'])
    commune_known_current = []
    first_object = data_new['schweiz']['vorlagen'][0]
    for data_canton in first_object['kantone']:
        for data_commune in data_canton['gemeinden']:
            if data_commune['resultat']["jaStimmenAbsolut"] is not None:
                commune_known_current.append(data_commune['geoLevelnummer'])
    new_commune = set(commune_known_current) - set(commune_known_previous)
    return new_commune

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
                except:
                    print(f'Commune not found: {data_commune["geoLevelnummer"]}: {data_commune["geoLevelname"]}')
                if (commune.nom in ['Rüti bei Lyssach', 'Jaberg']):
                    continue
                result = data_commune['resultat']
                scrutin = ScrutinEnCours(commune = commune,
                                         electeur_election_precedente = commune.nb_voix,
                                         sujet_vote = sujet,
                                         nombre_oui = result["jaStimmenAbsolut"],
                                         nombre_non = result["neinStimmenAbsolut"],
                                         electeurs_inscrits=result["anzahlStimmberechtigte"],
                                         bulletins_rentres=result["eingelegteStimmzettel"],
                                         comptabilise = True
                                         )
                scrutin.save()

def run():
    commune_to_import = get_new_commune("../data/votation_septembre_2022_1.json", "json_fake.json")
    import_votation("json_fake.json", commune_to_import)