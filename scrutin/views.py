from django.http import HttpResponse
from django.shortcuts import render

# Create your views here.
def home_view(requete, *args, **kwargs):
    #return HttpResponse("<h1> Bonjour, monde</h1>")
    return render(requete, "home.html", {})