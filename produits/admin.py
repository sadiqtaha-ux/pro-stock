"""
App Produits - Administration
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.db.models import Sum, F

from .models import Produit, Fournisseur, CategorieProduit, UniteMesure, LotProduit, TarifFournisseur


@admin.register(UniteMesure)
class UniteMesureAdmin(admin.ModelAdmin):
    list_display = ['code', 'libelle', 'categorie', 'est_actif']
    list_filter = ['categorie', 'est_actif']
    search_fields = ['code', 'libelle']


@admin.register(CategorieProduit)
class CategorieProduitAdmin(admin.ModelAdmin):
    list_display = ['code', 'libelle', 'parent', 'badge_couleur', 'est_actif']
    list_filter = ['est_actif']
    search_fields = ['code', 'libelle']

    @admin.display(description=_('Couleur'))
    def badge_couleur(self, obj):
        return format_html(
            '<span style="background:{};width:20px;height:20px;display:inline-block;border-radius:3px;"></span>',
            obj.couleur
        )


class TarifFournisseurInline(admin.TabularInline):
    model = TarifFournisseur
    extra = 1
    fields = ['fournisseur', 'prix_unitaire', 'remise', 'date_validite_debut', 'est_principal']


class LotProduitInline(admin.TabularInline):
    model = LotProduit
    extra = 0
    fields = ['numero_lot', 'quantite_restante', 'date_peremption', 'statut']
    readonly_fields = ['quantite_restante']


@admin.register(Produit)
class ProduitAdmin(admin.ModelAdmin):
    list_display = [
        'code', 'designation', 'categorie', 'badge_statut_stock',
        'stock_actuel', 'stock_minimum', 'unite_stock',
        'prix_unitaire_revient', 'classe_abc', 'statut'
    ]
    list_filter = ['statut', 'categorie', 'classe_abc', 'type_stockage', 'methode_appro']
    search_fields = ['code', 'designation', 'code_barre']
    readonly_fields = ['date_creation', 'date_modification', 'valeur_stock_display']
    inlines = [TarifFournisseurInline, LotProduitInline]
    list_per_page = 30

    fieldsets = (
        (_('Identification'), {
            'fields': ('code', 'code_barre', 'designation', 'description', 'photo', 'statut')
        }),
        (_('Classification'), {
            'fields': ('categorie', 'classe_abc', 'fournisseur_principal', 'emplacement')
        }),
        (_('Unités'), {
            'fields': ('unite_stock', 'unite_achat', 'coefficient_conversion')
        }),
        (_('Stock'), {
            'fields': (
                'stock_actuel', 'stock_minimum', 'stock_securite', 'stock_maximum',
                'point_commande', 'quantite_economique', 'valeur_stock_display'
            )
        }),
        (_('Prix'), {
            'fields': ('prix_unitaire_achat', 'prix_unitaire_revient', 'tva')
        }),
        (_('Stockage'), {
            'fields': ('type_stockage', 'temperature_min', 'temperature_max', 'duree_conservation')
        }),
        (_('Approvisionnement'), {
            'fields': ('methode_appro', 'delai_reappro', 'periodicite_reappro')
        }),
        (_('Audit'), {
            'fields': ('date_creation', 'date_modification', 'cree_par', 'modifie_par'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description=_('Statut stock'))
    def badge_statut_stock(self, obj):
        badges = {
            'rupture': ('#dc3545', '🔴 Rupture'),
            'alerte': ('#fd7e14', '⚠️ Alerte'),
            'surstock': ('#0dcaf0', '📈 Surstock'),
            'normal': ('#198754', '✅ Normal'),
        }
        color, label = badges.get(obj.statut_stock, ('#6c757d', '—'))
        return format_html(
            '<span style="color:{};">{}</span>', color, label
        )

    @admin.display(description=_('Valeur en stock'))
    def valeur_stock_display(self, obj):
        return f"{obj.valeur_stock:,.2f} DH"


@admin.register(Fournisseur)
class FournisseurAdmin(admin.ModelAdmin):
    list_display = ['code', 'raison_sociale', 'ville', 'telephone', 'email', 'statut', 'note_evaluation']
    list_filter = ['statut', 'pays', 'note_evaluation']
    search_fields = ['code', 'raison_sociale', 'email', 'ice']
    readonly_fields = ['date_creation', 'date_modification']


@admin.register(LotProduit)
class LotProduitAdmin(admin.ModelAdmin):
    list_display = ['produit', 'numero_lot', 'quantite_restante', 'date_peremption', 'badge_etat', 'statut']
    list_filter = ['statut', 'date_peremption']
    search_fields = ['numero_lot', 'produit__code', 'produit__designation']
    date_hierarchy = 'date_peremption'

    @admin.display(description=_('État'))
    def badge_etat(self, obj):
        if obj.est_perime:
            return format_html('<span style="color:#dc3545;">⛔ Périmé</span>')
        elif obj.est_proche_peremption:
            return format_html('<span style="color:#fd7e14;">⚠️ Proche péremption</span>')
        return format_html('<span style="color:#198754;">✅ OK</span>')
