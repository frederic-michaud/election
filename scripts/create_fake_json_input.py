from scrutin.models import Commune, Canton, District, Voix, SujetVote
import pandas as pd
import numpy as np
import json

p_rejection = 0.75

def get_result(commune, sujet):
    voixs = Voix.objects.filter(commune = commune, sujet_vote = sujet)
    if len(voixs) > 0:
        return voixs[0]
    return None


def run():
    path_votation = "../data/votation_septembre_2022.json"
    sujets = SujetVote.objects.order_by("date")
    with open(path_votation, 'r') as f:
        data = json.load(f)
    for index_sujet, sujet_vote_json in enumerate(data['schweiz']['vorlagen']):
        sujet = sujets[index_sujet]
        for data_canton in sujet_vote_json['kantone']:
            for data_commune in data_canton['gemeinden']:
                try:
                    commune = Commune.get_unique_commune_by_ofs(data_commune['geoLevelnummer'])
                except:
                    print(f'Commune not found: {data_commune["geoLevelnummer"]}: {data_commune["geoLevelname"]}')
                if (commune.nom in ['Rüti bei Lyssach', 'Jaberg']):
                    continue
                resultat_previous = get_result(commune, sujet)
                if resultat_previous == None:
                    continue
                if np.random.random() > p_rejection:
                    resultat_json = data_commune['resultat']
                    resultat_json["jaStimmenAbsolut"] = resultat_previous.nombre_oui
                    resultat_json["neinStimmenAbsolut"] = resultat_previous.nombre_non
                    resultat_json["anzahlStimmberechtigte"] = resultat_previous.electeurs_inscrits
                    resultat_json["eingelegteStimmzettel"] = resultat_previous.bulletins_rentres

    with open("json_fake.json", 'w') as f:
        json.dump(data, f)
