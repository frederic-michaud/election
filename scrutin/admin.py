from django.contrib import admin

from .models import (
    Anomalie,
    Canton,
    Commune,
    District,
    ResultatCommunalEnCours,
    ResultatCommunalHistorique,
    SujetVote,
)

admin.site.register(SujetVote)
admin.site.register(Commune)
admin.site.register(ResultatCommunalHistorique)
admin.site.register(Canton)
admin.site.register(District)
admin.site.register(ResultatCommunalEnCours)


@admin.register(Anomalie)
class AnomalieAdmin(admin.ModelAdmin):
    """La note libre s'écrit ici ; le reste est recalculé à chaque tour."""
    list_display = ("commune", "date", "niveau", "chi2", "chi2_corrige", "note")
    list_filter = ("date", "niveau")
    search_fields = ("commune__nom",)
    fields = ("commune", "date", "niveau", "note")
    readonly_fields = ("commune", "date", "niveau")
