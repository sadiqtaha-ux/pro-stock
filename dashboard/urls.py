"""dashboard/urls.py"""
from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    # Dashboard principal
    path("", views.DashboardIndexView.as_view(), name="index"),

    # APIs graphiques (JSON)
    path("api/mouvements/",   views.api_graphique_mouvements, name="api-mouvements"),
    path("api/valorisation/", views.api_graphique_valorisation, name="api-valorisation"),
    path("api/kpis/",         views.api_kpis, name="api-kpis"),

    # Rapports
    path("rapports/",          views.RapportIndexView.as_view(),  name="rapports"),
    path("rapports/stock/pdf/", views.generer_rapport_stock,      name="rapport-stock-pdf"),
]
