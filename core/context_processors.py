"""
App Core - Context Processors
Données disponibles dans tous les templates
"""

from django.conf import settings


def company_info(request):
    """Informations de l'entreprise disponibles dans tous les templates."""
    return {
        'COMPANY_INFO': settings.COMPANY_INFO,
        'APP_NAME': 'StockPro',
        'APP_VERSION': '1.0.0',
    }


def stock_alerts_count(request):
    """Nombre d'alertes de stock critiques."""
    if not request.user.is_authenticated:
        return {'nb_alertes_stock': 0, 'nb_notifications_non_lues': 0}

    try:
        from produits.models import Produit
        nb_alertes = Produit.objects.filter(
            stock_actuel__lte=models_f('stock_minimum'),
            est_actif=True,
        ).count()
    except Exception:
        nb_alertes = 0

    try:
        nb_notifs = request.user.notifications.filter(lue=False).count()
    except Exception:
        nb_notifs = 0

    return {
        'nb_alertes_stock': nb_alertes,
        'nb_notifications_non_lues': nb_notifs,
    }


def navigation_perms(request):
    """Permissions de navigation selon le rôle."""
    if not request.user.is_authenticated:
        return {}

    return {
        'peut_administrer': getattr(request.user, 'est_admin', False),
        'peut_valider': getattr(request.user, 'peut_valider', False),
        'peut_saisir': getattr(request.user, 'peut_saisir', True),
    }
