"""
mouvements/urls.py
Personne 2 — Backend Stocks
"""
from django.urls import path, reverse_lazy
from django.views.generic import RedirectView
from . import views

app_name = "mouvements"

urlpatterns = [
    # Liste complète
    path("",                views.MouvementListeView.as_view(), name="liste"),
    # Créer un mouvement
    path("nouveau/",        views.MouvementCreerView.as_view(), name="create"),
    # Redirections des anciennes URLs pour ne pas casser l'historique
    path("entrees/",        RedirectView.as_view(url="/mouvements/nouveau/?type=ENTREE", permanent=False), name="entree-liste"),
    path("sorties/",        RedirectView.as_view(url="/mouvements/nouveau/?type=SORTIE", permanent=False), name="sortie-liste"),
    # État du stock
    path("etat/",           views.EtatStockView.as_view(),      name="etat-stock"),
    # API JSON pour le dashboard (Personne 4)
    path("api/etat/",       views.api_etat_stock,               name="api-etat-stock"),
]
