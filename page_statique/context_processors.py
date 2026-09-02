from page_statique.models import PageStatique


def menu(requete):
    """Les pages éditables, pour que `base.html` en fasse ses onglets.

    Le menu était écrit en dur dans le gabarit : ajouter une page en base ne
    créait aucun onglet, et il fallait de toute façon éditer le HTML.
    """
    return {"pages_statiques": PageStatique.objects.order_by("ordre", "titre")}
