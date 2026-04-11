"""
StockPro - init du package stockpro
Chargement automatique de Celery au démarrage
"""

from .celery import app as celery_app

__all__ = ('celery_app',)
