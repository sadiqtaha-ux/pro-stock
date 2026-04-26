"""dashboard/urls.py"""
from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    # Dashboard principal
    path("", views.DashboardIndexView.as_view(), name="index"),
    path("alertes/", views.AlertesView.as_view(), name="alertes"),

    # APIs graphiques (JSON)
    path("api/mouvements/",   views.api_graphique_mouvements, name="api-mouvements"),
    path("api/valorisation/", views.api_graphique_valorisation, name="api-valorisation"),
    path("api/stock-statut/", views.api_graphique_stock_statut, name="api-stock-statut"),
    path("api/abc/",          views.api_graphique_abc,          name="api-abc"),
    path("api/commandes/",    views.api_graphique_commandes_statut, name="api-commandes-statut"),
    path("api/magasin/",      views.api_graphique_magasin_occupation, name="api-magasin-occupation"),
    path("api/kpis/",         views.api_kpis, name="api-kpis"),
    path("api/notifications/", views.api_notifications, name="api-notifications"),

    # Rapports
    path("rapports/",                   views.RapportIndexView.as_view(),  name="rapports"),
    
    # Détails des rapports
    path("rapports/stock/",             views.RapportStockView.as_view(),         name="rapport-stock-detail"),
    path("rapports/abc/",               views.RapportABCView.as_view(),           name="rapport-abc-detail"),
    path("rapports/mouvements/",        views.RapportMouvementsView.as_view(),    name="rapport-mouvements-detail"),
    path("rapports/appro/",             views.RapportApproView.as_view(),         name="rapport-appro-detail"),
    path("rapports/fournisseurs/",      views.RapportFournisseursView.as_view(),  name="rapport-fournisseurs-detail"),
    path("rapports/mrp/",               views.RapportMRPView.as_view(),           name="rapport-mrp-detail"),
    path("rapports/magasin/",           views.RapportMagasinView.as_view(),       name="rapport-magasin-detail"),
    path("rapports/produits-finis/",    views.RapportProduitsFinisView.as_view(), name="rapport-produits-finis-detail"),

    # Exports (PDF/CSV)
    path("rapports/<str:type_rapport>/export/<str:format_file>/", views.exporter_rapport, name="export-rapport"),
]
