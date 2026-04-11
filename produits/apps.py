"""
App Produits - Configuration
"""

from django.apps import AppConfig


class ProduitsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'produits'
    verbose_name = 'Produits — Matières Premières & Fournisseurs'

    def ready(self):
        import produits.signals  # noqa: F401
