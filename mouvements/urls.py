"""mouvements/urls.py"""
from django.urls import path
from . import views

app_name = "mouvements"

urlpatterns = [
    path("",           views.MouvementListeView.as_view(), name="liste"),
    path("nouveau/",   views.MouvementCreerView.as_view(), name="create"),
    path("entrees/",   views.EntreeListeView.as_view(),    name="entree-liste"),
    path("sorties/",   views.SortieListeView.as_view(),    name="sortie-liste"),
]
