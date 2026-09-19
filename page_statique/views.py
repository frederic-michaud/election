import logging

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.core.validators import validate_email
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from page_statique.models import PageStatique

logger = logging.getLogger(__name__)


def static_view(requete, url):
    page = get_object_or_404(PageStatique, url=url)
    return render(requete, "static.html", {"page_content": page})


# Sans jeton CSRF, pour que la page Contact reste identique pour tous, donc
# cachable. Un site tiers ne pourrait que nous envoyer un message.
@csrf_exempt
@require_POST
def envoyer_contact(requete):
    """Transmet le message du formulaire Contact par courriel."""
    def reponse(erreur=None, statut=200):
        return render(requete, "contact_reponse.html", {"erreur": erreur}, status=statut)

    # Pot de miel : champ invisible qu'un humain laisse vide. On ne dit rien au robot.
    if requete.POST.get("site_web"):
        return reponse()

    nom = " ".join(requete.POST.get("nom", "").split())[:100]  # une seule ligne
    courriel = requete.POST.get("courriel", "").strip()
    message = requete.POST.get("message", "").strip()[:5000]
    try:
        validate_email(courriel)
    except ValidationError:
        return reponse("Il manque une adresse e-mail valide pour vous répondre.", 400)
    if not message:
        return reponse("Votre message est vide.", 400)

    if not settings.CONTACT_DESTINATAIRE:
        logger.warning("CONTACT_DESTINATAIRE vide : message de %s perdu", courriel)
        return reponse("Le formulaire n'est pas encore relié à notre messagerie. "
                       "Réessayez dans quelques jours.", 503)
    try:
        EmailMessage(
            subject=f"[Politiques.ch] Message de {nom or courriel}",
            body=f"{message}\n\n— {nom or 'Sans nom'} <{courriel}>",
            to=[settings.CONTACT_DESTINATAIRE],
            reply_to=[courriel],
        ).send()
    except Exception:
        logger.exception("Échec de l'envoi du formulaire de contact")
        return reponse("L'envoi a échoué de notre côté. Réessayez un peu plus tard.", 502)
    return reponse()
