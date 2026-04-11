"""
App Mouvements - URLs
"""

from django.urls import path
from . import views

app_name = 'mouvements'

urlpatterns = [
    # Historique global
    path('', views.HistoriqueMouvementsView.as_view(), name='historique'),

    # Entrées (Bons d'entrée)
    path('entrees/', views.BonEntreeListeView.as_view(), name='entree-liste'),
    path('entrees/nouveau/', views.BonEntreeCreerView.as_view(), name='entree-creer'),
    path('entrees/<int:pk>/', views.BonEntreeDetailView.as_view(), name='entree-detail'),
    path('entrees/<int:pk>/valider/', views.valider_bon_entree, name='entree-valider'),

    # Sorties (Bons de sortie)
    path('sorties/', views.BonSortieListeView.as_view(), name='sortie-liste'),
    path('sorties/nouveau/', views.BonSortieCreerView.as_view(), name='sortie-creer'),
    path('sorties/<int:pk>/', views.BonSortieDetailView.as_view(), name='sortie-detail'),
    path('sorties/<int:pk>/valider/', views.valider_bon_sortie, name='sortie-valider'),

    # Inventaires
    path('inventaires/', views.InventaireListeView.as_view(), name='inventaire-liste'),
    path('inventaires/nouveau/', views.InventaireCreerView.as_view(), name='inventaire-creer'),
    path('inventaires/<int:pk>/', views.InventaireDetailView.as_view(), name='inventaire-detail'),
]
