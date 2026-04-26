"""
App Magasin - URLs
"""

from django.urls import path
from . import views

app_name = 'magasin'

urlpatterns = [
    # Plan 2D interactif
    path('', views.PlanMagasinView.as_view(), name='plan'),

    # API temps réel pour la vue 2D (Nouvelle version)
    path('api/plan/', views.api_plan_data, name='api-plan'),
    path('api/plan/positions/', views.api_bulk_positions, name='api-bulk-positions'),
    path('api/detail/<str:ref>/', views.api_emplacement_detail, name='api-detail'),

    # APIs CRUD pour l'éditeur 2D
    path('api/zones/', views.api_zone_create, name='api-zone-create'),
    path('api/zones/<int:pk>/', views.api_zone_patch, name='api-zone-patch'),
    path('api/zones/<int:pk>/delete/', views.api_zone_delete, name='api-zone-delete'),

    path('api/rayons/', views.api_rayon_create, name='api-rayon-create'),
    path('api/rayons/<int:pk>/', views.api_rayon_patch, name='api-rayon-patch'),
    path('api/rayons/<int:pk>/delete/', views.api_rayon_delete, name='api-rayon-delete'),

    path('api/affectations/', views.api_affectation_create, name='api-affectation-create'),
    path('api/affectations/<int:pk>/delete/', views.api_affectation_delete, name='api-affectation-delete'),

    path('api/delimitations/', views.api_delimitation_create, name='api-delimitation-create'),
    path('api/delimitations/<int:pk>/', views.api_delimitation_patch, name='api-delimitation-patch'),
    path('api/delimitations/<int:pk>/delete/', views.api_delimitation_delete, name='api-delimitation-delete'),

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
