"""
App Approvisionnement - URLs
"""

from django.urls import path
from . import views

app_name = 'approvisionnement'

urlpatterns = [
    # Tableau de bord approvisionnement
    path('', views.ApproDashboardView.as_view(), name='dashboard'),

    # Commandes d'achat
    path('commandes/', views.CommandeListeView.as_view(), name='commande-liste'),
    path('commandes/nouvelle/', views.CommandeCreerView.as_view(), name='commande-creer'),
    path('commandes/<int:pk>/', views.CommandeDetailView.as_view(), name='commande-detail'),
    path('commandes/<int:pk>/modifier/', views.CommandeModifierView.as_view(), name='commande-modifier'),
    path('commandes/<int:pk>/valider/', views.valider_commande, name='commande-valider'),

    # Méthode 1 : Réappro Fixe
    path('methodes/reappro-fixe/', views.ReapproFixeView.as_view(), name='methode-reappro-fixe'),

    # Méthode 2 : Point de Commande (ROP)
    path('methodes/point-commande/', views.PointCommandeView.as_view(), name='methode-point-commande'),

    # Méthode 3 : Récompletement (S,T)
    path('methodes/recompletement/', views.RecompletementView.as_view(), name='methode-recompletement'),

    # Méthode 4 : MRP
    path('mrp/', views.MRPListeView.as_view(), name='mrp-liste'),
    path('mrp/nouveau/', views.MRPCreerView.as_view(), name='mrp-creer'),
    path('mrp/<int:pk>/', views.MRPDetailView.as_view(), name='mrp-detail'),
    path('mrp/<int:pk>/calculer/', views.lancer_calcul_mrp, name='mrp-calculer'),

    # Suggestions
    path('suggestions/', views.SuggestionListeView.as_view(), name='suggestions-liste'),
    path('suggestions/<int:pk>/transformer/', views.transformer_suggestion_en_commande, name='suggestion-transformer'),

    # Paramètres d'approvisionnement
    path('parametres/', views.ParametreApproView.as_view(), name='parametres'),
    path('parametres/<int:produit_pk>/calculer/', views.calculer_parametres_produit, name='parametres-calculer'),
]
