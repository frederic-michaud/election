from django.contrib import admin

# Register your models here.
from .models import SujetVote, Commune, Voix, Canton, District

admin.site.register(SujetVote)
admin.site.register(Commune)
admin.site.register(Voix)
admin.site.register(Canton)
admin.site.register(District)