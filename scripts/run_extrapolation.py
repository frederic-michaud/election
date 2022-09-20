from scrutin.extrapolation import get_extrapolation
from scrutin.models import SujetVote, Extrapolation

def run():
    last_sujet = SujetVote.objects.latest('date')
    sujets = SujetVote.objects.filter(date = last_sujet.date)
    for sujet in sujets:
        deja_comptabilise, extrapole, avance, voixs, percent_oui, percent_vote = get_extrapolation(sujet)
        for voix, extrapolation_oui, extrapolation_voters in zip(voixs, percent_oui, percent_vote):
            voix.nombre_oui = extrapolation_oui*extrapolation_voters*voix.electeur_election_precedente
            voix.bulletins_rentres = extrapolation_voters * voix.electeur_election_precedente
            voix.nombre_non = voix.bulletins_rentres - voix.nombre_oui
            voix.save()
        extrapolation = Extrapolation(sujet_vote=sujet, pourcentage_oui_connu=deja_comptabilise,
                                      pourcentage_oui_extrapole=extrapole, avance=avance)
        extrapolation.save()