"""
App Produits - URLs
"""

from django.urls import path
from . import views

app_name = 'produits'

urlpatterns = [
    # Produits
    path('', views.ProduitListeView.as_view(), name='produit-liste'),
    path('nouveau/', views.ProduitCreerView.as_view(), name='produit-creer'),
    path('<int:pk>/', views.ProduitDetailView.as_view(), name='produit-detail'),
    path('<int:pk>/modifier/', views.ProduitModifierView.as_view(), name='produit-modifier'),

    # Fournisseurs
    path('fournisseurs/', views.FournisseurListeView.as_view(), name='fournisseur-liste'),
    path('fournisseurs/nouveau/', views.FournisseurCreerView.as_view(), name='fournisseur-creer'),
    path('fournisseurs/<int:pk>/', views.FournisseurDetailView.as_view(), name='fournisseur-detail'),
    path('fournisseurs/<int:pk>/modifier/', views.FournisseurModifierView.as_view(), name='fournisseur-modifier'),

    # Catégories
    path('categories/', views.CategorieListeView.as_view(), name='categorie-liste'),

    # Unités de mesure
    path('unites/', views.UniteMesureListeView.as_view(), name='unite-liste'),

    # Lots
    path('lots/', views.LotListeView.as_view(), name='lot-liste'),

    # API
    path('api/search/', views.produit_search_api, name='api-search'),
]
