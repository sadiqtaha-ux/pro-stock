"""
App Dashboard - URLs
"""

from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Dashboard principal
    path('', views.DashboardIndexView.as_view(), name='index'),

    # APIs graphiques (JSON)
    path('api/mouvements/', views.api_graphique_mouvements, name='api-mouvements'),
    path('api/valorisation/', views.api_graphique_valorisation_categories, name='api-valorisation'),
    path('api/abc/', views.api_graphique_abc, name='api-abc'),
    path('api/kpis/', views.api_kpis_temps_reel, name='api-kpis'),

    # Rapports
    path('rapports/', views.RapportIndexView.as_view(), name='rapports'),
    path('rapports/stock/pdf/', views.generer_rapport_stock, name='rapport-stock-pdf'),
    path('rapports/abc/', views.AnalyseABCView.as_view(), name='rapport-abc'),
]
