"""approvisionnement/urls.py"""
from django.urls import path
from . import views

app_name = "approvisionnement"

urlpatterns = [
    # Tableau de bord
    path("",                          views.ApproDashboardView.as_view(),    name="dashboard"),

    # Bons de commande
    path("commandes/",                views.BonCommandeListeView.as_view(),  name="commande-liste"),
    path("commandes/nouveau/",        views.BonCommandeCreerView.as_view(),  name="commande-create"),
    path("commandes/<int:pk>/",       views.BonCommandeDetailView.as_view(), name="commande-detail"),
    path("commandes/<int:pk>/modifier/", views.BonCommandeModifierView.as_view(), name="commande-update"),

    # Plans MRP
    path("mrp/",                      views.PlanMRPListeView.as_view(),      name="mrp-liste"),
    path("mrp/nouveau/",              views.PlanMRPCreerView.as_view(),      name="mrp-create"),

    # Méthodes de calcul
    path("methodes/reappro-fixe/",    views.ReapproFixeView.as_view(),       name="reappro-fixe"),
    path("methodes/point-commande/",  views.PointCommandeView.as_view(),     name="point-commande"),
    path("methodes/recompletement/",  views.RecompletementView.as_view(),    name="recompletement"),
]
