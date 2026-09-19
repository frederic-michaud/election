"""election URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.views.generic import RedirectView

from carte.views import carte_view
from page_statique.views import static_view
from pca.views import nuage_communes_view, nuage_objets_view
from scrutin.views import home_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path("", home_view, name="home"),
    path("cartes", carte_view, name="cartes"),
    path("nuage-acp", nuage_communes_view, name="nuage_acp"),
    path("objets-acp", nuage_objets_view, name="objets_acp"),
    path("pca", RedirectView.as_view(pattern_name="nuage_acp")),
    path("<slug:url>", static_view, name="page"),
]
