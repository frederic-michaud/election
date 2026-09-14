from django import template
from plotly.offline import get_plotlyjs_version

register = template.Library()


@register.simple_tag
def plotly_cdn():
    """plotly.js sur le CDN, à la version qu'attend le paquet Python installé."""
    return f"https://cdn.plot.ly/plotly-{get_plotlyjs_version()}.min.js"
