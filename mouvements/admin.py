"""
App Mouvements - Administration
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html

from .models import MouvementStock, BonEntree, BonSortie, Inventaire, LigneInventaire


@admin.register(MouvementStock)
class MouvementStockAdmin(admin.ModelAdmin):
    list_display = ['numero', 'type_mouvement', 'produit', 'quantite', 'unite', 'statut', 'date_mouvement', 'cree_par']
    list_filter = ['type_mouvement', 'statut', 'date_mouvement']
    search_fields = ['numero', 'produit__code', 'produit__designation', 'reference_document']
    readonly_fields = ['numero', 'stock_avant', 'stock_apres', 'date_creation']
    date_hierarchy = 'date_mouvement'
    ordering = ['-date_mouvement']


class LignesMouvementsInline(admin.TabularInline):
    model = MouvementStock
    extra = 0
    fields = ['produit', 'lot', 'quantite', 'prix_unitaire', 'statut']
    fk_name = 'commande'


@admin.register(BonEntree)
class BonEntreeAdmin(admin.ModelAdmin):
    list_display = ['numero', 'fournisseur', 'date_reception', 'statut', 'valide_par']
    list_filter = ['statut', 'date_reception']
    search_fields = ['numero', 'fournisseur__raison_sociale', 'reference_fournisseur']
    readonly_fields = ['numero', 'date_creation']
    date_hierarchy = 'date_reception'


@admin.register(BonSortie)
class BonSortieAdmin(admin.ModelAdmin):
    list_display = ['numero', 'demandeur', 'service_demandeur', 'date_demande', 'statut']
    list_filter = ['statut', 'date_demande']
    search_fields = ['numero', 'service_demandeur', 'motif']
    readonly_fields = ['numero', 'date_creation']


class LigneInventaireInline(admin.TabularInline):
    model = LigneInventaire
    extra = 0
    fields = ['produit', 'lot', 'quantite_theorique', 'quantite_comptee', 'ecart']
    readonly_fields = ['ecart']


@admin.register(Inventaire)
class InventaireAdmin(admin.ModelAdmin):
    list_display = ['numero', 'type_inventaire', 'date_debut', 'date_fin', 'responsable', 'statut']
    list_filter = ['statut', 'type_inventaire']
    search_fields = ['numero']
    inlines = [LigneInventaireInline]
    readonly_fields = ['numero']
