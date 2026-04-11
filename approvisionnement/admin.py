"""
App Approvisionnement - Administration
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html

from .models import (
    CommandeAchat, LigneCommandeAchat,
    SuggestionAppro, ParametreAppro,
    PlanMRP, LigneMRP
)


class LigneCommandeInline(admin.TabularInline):
    model = LigneCommandeAchat
    extra = 1
    fields = ['produit', 'quantite_commandee', 'unite', 'prix_unitaire_ht', 'remise', 'tva']


@admin.register(CommandeAchat)
class CommandeAchatAdmin(admin.ModelAdmin):
    list_display = ['numero', 'fournisseur', 'type_commande', 'date_commande', 'badge_statut', 'montant_ttc']
    list_filter = ['statut', 'type_commande', 'methode_declenchement', 'date_commande']
    search_fields = ['numero', 'fournisseur__raison_sociale']
    readonly_fields = ['numero', 'date_creation', 'montant_ht', 'montant_tva', 'montant_ttc']
    inlines = [LigneCommandeInline]
    date_hierarchy = 'date_commande'

    @admin.display(description=_('Statut'))
    def badge_statut(self, obj):
        couleurs = {
            'BROUILLON': '#6c757d',
            'VALIDATION': '#ffc107',
            'VALIDE': '#0d6efd',
            'ENVOYE': '#0dcaf0',
            'PARTIEL': '#fd7e14',
            'RECU': '#198754',
            'ANNULE': '#dc3545',
            'CLOTURE': '#495057',
        }
        couleur = couleurs.get(obj.statut, '#6c757d')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;">{}</span>',
            couleur, obj.get_statut_display()
        )


@admin.register(SuggestionAppro)
class SuggestionApproAdmin(admin.ModelAdmin):
    list_display = ['produit', 'methode', 'quantite_suggeree', 'date_suggestion', 'statut', 'urgente']
    list_filter = ['methode', 'statut', 'urgente']
    search_fields = ['produit__code', 'produit__designation']
    readonly_fields = ['date_creation']


@admin.register(ParametreAppro)
class ParametreApproAdmin(admin.ModelAdmin):
    list_display = ['produit', 'methode', 'consommation_journaliere_moyenne', 'delai_reappro_jours', 'qec_calcule']
    list_filter = ['methode']
    search_fields = ['produit__code', 'produit__designation']


class LigneMRPInline(admin.TabularInline):
    model = LigneMRP
    extra = 0
    fields = ['produit', 'semaine', 'annee', 'besoin_brut', 'besoin_net', 'ordre_propose']
    readonly_fields = ['besoin_net']


@admin.register(PlanMRP)
class PlanMRPAdmin(admin.ModelAdmin):
    list_display = ['numero', 'description', 'date_debut', 'date_fin', 'horizon_semaines', 'statut']
    list_filter = ['statut']
    search_fields = ['numero', 'description']
    readonly_fields = ['numero', 'date_creation']
    inlines = [LigneMRPInline]
