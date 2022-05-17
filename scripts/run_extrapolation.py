from scrutin.extrapolation import get_extrapolation
from scrutin.models import SujetVote, Extrapolation

def run():
    last_sujet = SujetVote.objects.latest('date')
    sujets = SujetVote.objects.filter(date = last_sujet.date)
    for sujet in sujets:
        deja_comptabilise, extrapole, avance = get_extrapolation(sujet)
        extrapolation = Extrapolation(sujet_vote=sujet, pourcentage_oui_connu=deja_comptabilise,
                                      pourcentage_oui_extrapole=extrapole, avance=avance)
        extrapolation.save()