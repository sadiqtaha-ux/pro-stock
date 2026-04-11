"""
App Magasin - Configuration
"""

from django.apps import AppConfig


class MagasinConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'magasin'
    verbose_name = 'Magasin — Plan 2D & Emplacements'
