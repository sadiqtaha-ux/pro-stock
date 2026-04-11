"""
App Approvisionnement - Configuration
"""

from django.apps import AppConfig


class ApprovisionnementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'approvisionnement'
    verbose_name = 'Approvisionnement — Commandes & Méthodes'

    def ready(self):
        import approvisionnement.signals  # noqa: F401
