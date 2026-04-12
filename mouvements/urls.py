"""
mouvements/urls.py
Personne 2 — Backend Stocks
"""
from django.urls import path
from . import views

app_name = "mouvements"

urlpatterns = [
    # Liste complète
    path("",                views.MouvementListeView.as_view(), name="liste"),
    # Créer un mouvement
    path("nouveau/",        views.MouvementCreerView.as_view(), name="create"),
    # Entrées uniquement
    path("entrees/",        views.EntreeListeView.as_view(),    name="entree-liste"),
    # Sorties uniquement
    path("sorties/",        views.SortieListeView.as_view(),    name="sortie-liste"),
    # État du stock
    path("etat/",           views.etat_stock_view,              name="etat-stock"),
    # Export CSV
    path("export/csv/",     views.export_csv_view,              name="export-csv"),
    # API JSON pour le dashboard (Personne 4)
    path("api/etat/",       views.api_etat_stock,               name="api-etat-stock"),
]
