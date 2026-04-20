"""
App Magasin - URLs
"""

from django.urls import path
from . import views

app_name = 'magasin'

urlpatterns = [
    # Plan 2D interactif
    path('', views.PlanMagasinView.as_view(), name='plan'),

    # API temps réel pour la vue 2D
    path('api/plan/', views.api_plan_temps_reel, name='api-plan'),
    path('api/detail/<str:ref>/', views.api_emplacement_detail, name='api-detail'),

    # Zones
    path('zones/', views.ZoneListeView.as_view(), name='zone-liste'),
    path('zones/nouvelle/', views.ZoneCreerView.as_view(), name='zone-creer'),
    path('zones/<int:pk>/', views.ZoneDetailView.as_view(), name='zone-detail'),

    # Rayons
    path('rayons/', views.RayonListeView.as_view(), name='rayon-liste'),
    path('rayons/nouveau/', views.RayonCreerView.as_view(), name='rayon-creer'),

    # Emplacements
    path('emplacements/', views.EmplacementListeView.as_view(), name='emplacement-liste'),
    path('emplacements/nouveau/', views.EmplacementCreerView.as_view(), name='emplacement-creer'),
]
