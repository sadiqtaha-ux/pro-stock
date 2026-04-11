"""
App Produits - Signaux
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Produit, LotProduit


@receiver(post_save, sender=LotProduit)
def update_stock_on_lot_save(sender, instance, created, **kwargs):
    """
    Met à jour le stock_actuel du produit quand un lot change.
    """
    pass  # À implémenter avec la logique métier
