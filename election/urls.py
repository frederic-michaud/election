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
from scrutin.views import home_view
from pca.views import pca_view
from page_statique.views import static_view
from carte.views import carte_view
urlpatterns = [
    path('admin/', admin.site.urls),
    path("", home_view, name="home"),
    path("cartes", carte_view, name="cartes"),
    path("pca", pca_view, name="PCA"),
    path("<str>", static_view)
]
