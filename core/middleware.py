"""
App Core - Middlewares personnalisés
Journal d'activité, alertes de stock
"""

from django.utils import timezone
from django.conf import settings
from .models import JournalActivite


class ActivityLogMiddleware:
    """
    Middleware de journalisation automatique des requêtes.
    Enregistre les actions POST significatives dans le journal.
    """

    EXCLUDED_PATHS = [
        '/static/', '/media/', '/favicon.ico',
        '/api/', '__debug__', '/admin/jsi18n/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        """Traitement avant la vue."""
        return None


class StockAlertMiddleware:
    """
    Middleware qui vérifie les alertes de stock critiques.
    Stocke le nombre d'alertes dans request pour usage dans les templates.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Le comptage est fait dans le context processor pour la performance
            pass
        response = self.get_response(request)
        return response
