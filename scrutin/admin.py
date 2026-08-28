from django.contrib import admin

# Register your models here.
from .models import Canton, Commune, District, ScrutinEnCours, SujetVote, Voix

admin.site.register(SujetVote)
admin.site.register(Commune)
admin.site.register(Voix)
admin.site.register(Canton)
admin.site.register(District)
admin.site.register(ScrutinEnCours)
