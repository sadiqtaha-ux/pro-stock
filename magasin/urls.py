"""
App Magasin - URLs
"""

from django.urls import path
from . import views

app_name = 'magasin'

urlpatterns = [
    # Plan 2D interactif
    path('', views.PlanMagasinView.as_view(), name='plan'),
    path('api/plan/', views.api_plan_data, name='api-plan'),
    path('api/emplacements/<int:pk>/', views.api_emplacement_detail, name='api-emplacement'),

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
