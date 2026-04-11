"""
App Core - Administration Django
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html

from .models import Utilisateur, JournalActivite, Notification, ParametreApplication


# ============================================================
# UTILISATEUR
# ============================================================

@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
    """Administration des utilisateurs StockPro."""

    list_display = ['username', 'get_full_name', 'email', 'badge_role', 'service', 'est_actif', 'date_derniere_connexion']
    list_filter = ['role', 'est_actif', 'is_staff', 'date_joined']
    search_fields = ['username', 'first_name', 'last_name', 'email', 'service']
    ordering = ['last_name', 'first_name']

    fieldsets = UserAdmin.fieldsets + (
        (_('Informations StockPro'), {
            'fields': ('role', 'telephone', 'service', 'photo', 'est_actif', 'date_derniere_connexion'),
        }),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        (_('Informations StockPro'), {
            'fields': ('role', 'telephone', 'service', 'est_actif'),
        }),
    )

    @admin.display(description=_('Rôle'), ordering='role')
    def badge_role(self, obj):
        colors = {
            'ADMIN': '#dc3545',
            'RESPONSABLE_STOCK': '#0d6efd',
            'MAGASINIER': '#198754',
            'ACHETEUR': '#fd7e14',
            'CONSULTANT': '#6c757d',
        }
        color = colors.get(obj.role, '#6c757d')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;">{}</span>',
            color, obj.get_role_display()
        )


# ============================================================
# JOURNAL D'ACTIVITÉ
# ============================================================

@admin.register(JournalActivite)
class JournalActiviteAdmin(admin.ModelAdmin):
    """Administration du journal d'activité."""

    list_display = ['utilisateur', 'action', 'modele', 'objet_id', 'adresse_ip', 'date_action']
    list_filter = ['action', 'modele', 'date_action']
    search_fields = ['utilisateur__username', 'modele', 'description']
    readonly_fields = ['utilisateur', 'action', 'modele', 'objet_id', 'description',
                       'adresse_ip', 'date_action', 'donnees_avant', 'donnees_apres']
    ordering = ['-date_action']
    date_hierarchy = 'date_action'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


# ============================================================
# NOTIFICATION
# ============================================================

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Administration des notifications."""

    list_display = ['titre', 'destinataire', 'type_notification', 'priorite', 'lue', 'date_envoi']
    list_filter = ['type_notification', 'priorite', 'lue', 'date_envoi']
    search_fields = ['titre', 'message', 'destinataire__username']
    ordering = ['-date_envoi']
    date_hierarchy = 'date_envoi'


# ============================================================
# PARAMÈTRES APPLICATION
# ============================================================

@admin.register(ParametreApplication)
class ParametreApplicationAdmin(admin.ModelAdmin):
    """Administration des paramètres applicatifs."""

    list_display = ['cle', 'valeur', 'type_valeur', 'description', 'modifie_le']
    list_filter = ['type_valeur']
    search_fields = ['cle', 'description']
    ordering = ['cle']
