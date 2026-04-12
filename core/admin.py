"""
core/admin.py
Administration Django pour l'app Core — MediCare StockPro
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import Utilisateur, JournalActivite, Notification, ParametreApplication


# ─────────────────────────────────────────────
# UTILISATEUR
# ─────────────────────────────────────────────

@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
    list_display  = ("username", "get_full_name", "email", "role", "service", "est_actif", "date_joined")
    list_filter   = ("role", "est_actif", "is_staff")
    search_fields = ("username", "first_name", "last_name", "email")
    list_editable = ("role", "est_actif")
    ordering      = ("last_name", "first_name")

    # Ajout des champs custom dans le formulaire d'édition
    fieldsets = UserAdmin.fieldsets + (
        (_("Informations StockPro"), {
            "fields": ("role", "telephone", "photo", "service", "est_actif", "date_derniere_connexion"),
        }),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (_("Informations StockPro"), {
            "fields": ("role", "telephone", "service"),
        }),
    )
    readonly_fields = ("date_derniere_connexion",)


# ─────────────────────────────────────────────
# JOURNAL D'ACTIVITÉ
# ─────────────────────────────────────────────

@admin.register(JournalActivite)
class JournalActiviteAdmin(admin.ModelAdmin):
    list_display  = ("date_action", "utilisateur", "action", "modele", "objet_id", "adresse_ip")
    list_filter   = ("action", "modele")
    search_fields = ("utilisateur__username", "description", "objet_id")
    date_hierarchy = "date_action"
    readonly_fields = ("date_action", "donnees_avant", "donnees_apres")

    def has_add_permission(self, request):
        return False  # journal en lecture seule


# ─────────────────────────────────────────────
# NOTIFICATIONS
# ─────────────────────────────────────────────

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display  = ("titre", "destinataire", "type_notification", "priorite", "lue", "date_envoi")
    list_filter   = ("type_notification", "priorite", "lue")
    search_fields = ("titre", "destinataire__username")
    list_editable = ("lue",)
    date_hierarchy = "date_envoi"


# ─────────────────────────────────────────────
# PARAMÈTRES APPLICATION
# ─────────────────────────────────────────────

@admin.register(ParametreApplication)
class ParametreApplicationAdmin(admin.ModelAdmin):
    list_display  = ("cle", "valeur", "type_valeur", "modifie_le")
    list_filter   = ("type_valeur",)
    search_fields = ("cle", "description")
    readonly_fields = ("modifie_le",)
