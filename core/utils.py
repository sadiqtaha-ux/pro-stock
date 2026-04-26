"""
core/utils.py
Utilitaires pour l'application StockPro.
"""
from .models import JournalActivite

def log_action(request, action, modele, objet_id=None, description="", niveau=JournalActivite.Niveau.INFO, donnees_avant=None, donnees_apres=None):
    """
    Enregistre une action dans le journal d'activité.
    """
    utilisateur = None
    if request and request.user.is_authenticated:
        utilisateur = request.user
    
    adresse_ip = None
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            adresse_ip = x_forwarded_for.split(',')[0]
        else:
            adresse_ip = request.META.get('REMOTE_ADDR')

    return JournalActivite.objects.create(
        utilisateur=utilisateur,
        action=action,
        modele=modele,
        objet_id=str(objet_id) if objet_id else None,
        description=description,
        niveau=niveau,
        adresse_ip=adresse_ip,
        donnees_avant=donnees_avant,
        donnees_apres=donnees_apres
    )
