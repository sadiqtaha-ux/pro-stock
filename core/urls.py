"""
App Core - URLs
"""

from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Authentification
    path('', views.ConnexionView.as_view(), name='login'),
    path('connexion/', views.ConnexionView.as_view(), name='connexion'),
    path('deconnexion/', views.DeconnexionView.as_view(), name='logout'),
    path('deconnexion/', views.DeconnexionView.as_view(), name='deconnexion'),

    # Profil
    path('profil/', views.ProfilView.as_view(), name='profil'),

    # Gestion utilisateurs
    path('utilisateurs/', views.UtilisateurListeView.as_view(), name='utilisateurs-liste'),
    path('utilisateurs/nouveau/', views.UtilisateurCreerView.as_view(), name='utilisateurs-creer'),
    path('utilisateurs/<int:pk>/modifier/', views.UtilisateurModifierView.as_view(), name='utilisateurs-modifier'),

    # Notifications
    path('notifications/', views.NotificationsView.as_view(), name='notifications'),
    path('notifications/<int:pk>/lue/', views.marquer_notification_lue, name='notification-lue'),
    path('notifications/tout-lire/', views.marquer_toutes_lues, name='notifications-tout-lire'),

    # Journal d'activité
    path('journal/', views.JournalView.as_view(), name='journal'),

    # Paramètres
    path('parametres/', views.ParametresView.as_view(), name='parametres'),
]
