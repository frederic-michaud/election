from django.contrib import admin

# Register your models here.
from .models import (
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
