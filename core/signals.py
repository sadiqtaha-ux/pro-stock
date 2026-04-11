"""
App Core - Signaux Django
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.utils import timezone


@receiver(user_logged_in)
def on_user_logged_in(sender, request, user, **kwargs):
    """Signal déclenché à la connexion d'un utilisateur."""
    user.date_derniere_connexion = timezone.now()
    user.save(update_fields=['date_derniere_connexion'])


@receiver(user_logged_out)
def on_user_logged_out(sender, request, user, **kwargs):
    """Signal déclenché à la déconnexion."""
    pass


@receiver(user_login_failed)
def on_user_login_failed(sender, credentials, request, **kwargs):
    """Signal déclenché sur une tentative de connexion échouée."""
    pass
