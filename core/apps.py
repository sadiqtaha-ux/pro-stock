"""
App Core - Configuration
"""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'Core — Authentification & Base'

    def ready(self):
        """Importer les signaux au démarrage de l'application."""
        import core.signals  # noqa: F401
