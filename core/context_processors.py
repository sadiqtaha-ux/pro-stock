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
    """Nombre d'alertes de stock critiques et notifications non lues."""
    if not request.user.is_authenticated:
        return {'nb_alertes_stock': 0, 'nb_notifications_non_lues': 0}

    try:
        from produits.models import MatierePremiere, ProduitFini
        from approvisionnement.models import BonCommande, PropositionCommande
        from magasin.models import Emplacement
        from django.db.models import F
        from django.utils import timezone
        
        today = timezone.now().date()
        
        # Alertes système (pour le bouton jaune du header)
        nb_mp_crit = MatierePremiere.objects.filter(stock_actuel__lte=F('stock_minimum'), actif=True).count()
        nb_pf_crit = ProduitFini.objects.filter(stock_actuel__lte=F('stock_minimum'), actif=True).count()
        nb_retards = BonCommande.objects.filter(statut__in=['ENVOYE', 'CONFIRME'], date_reception_prevue__lt=today).count()
        nb_bloques = Emplacement.objects.filter(statut='BLOQUE').count()
        
        # Le bouton "Alertes" du header regroupe tout ce qui est critique/danger
        nb_alertes = nb_mp_crit + nb_pf_crit + nb_retards + nb_bloques
        
        # Notifications (pour le badge de la cloche) - plus large
        nb_notifs_db = request.user.notifications.filter(lue=False).count()
        nb_props = PropositionCommande.objects.filter(statut=PropositionCommande.Statut.EN_ATTENTE).count()
        
        total_notifs = nb_notifs_db + nb_props + nb_alertes # Tout ce qui mérite attention
        
    except Exception:
        nb_alertes = 0
        total_notifs = 0

    return {
        'nb_alertes_stock': nb_alertes,
        'nb_notifications_non_lues': total_notifs,
    }


def navigation_perms(request):
    """Permissions de navigation selon le rôle."""
    if not request.user.is_authenticated:
        return {}

    return {
        'peut_administrer': request.user.is_staff or request.user.is_superuser or getattr(request.user, 'est_admin', False),
        'peut_valider': getattr(request.user, 'peut_valider', False),
        'peut_saisir': getattr(request.user, 'peut_saisir', True),
    }
