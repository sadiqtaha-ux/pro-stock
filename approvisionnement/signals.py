"""
App Approvisionnement - Signaux
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _


@receiver(post_save, sender='approvisionnement.CommandeAchat')
def on_commande_validee(sender, instance, **kwargs):
    """Signal déclenché à la validation d'une commande."""
    if instance.statut == 'VALIDE':
        # Notifier le responsable des achats
        pass
