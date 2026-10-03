from page_statique.models import PageStatique


def menu(requete):
    """Les pages éditables, pour que `base.html` en fasse ses onglets."""
    return {"pages_statiques": PageStatique.objects.order_by("ordre", "titre")}
