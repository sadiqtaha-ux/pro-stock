"""
App Mouvements - Configuration
"""

from django.apps import AppConfig


class MouvementsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mouvements'
    verbose_name = 'Mouvements — Entrées & Sorties'
