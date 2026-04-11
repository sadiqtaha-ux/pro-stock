"""
App Magasin - Administration
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.db.models import Count, Q

from .models import ZoneStockage, Rayon, Emplacement, PlanMagasin


class RayonInline(admin.TabularInline):
    model = Rayon
    extra = 1
    fields = ['code', 'libelle', 'orientation', 'nombre_niveaux', 'nombre_colonnes']


@admin.register(ZoneStockage)
class ZoneStockageAdmin(admin.ModelAdmin):
    list_display = ['code', 'libelle', 'type_zone', 'badge_couleur', 'capacite_totale', 'est_actif']
    list_filter = ['type_zone', 'est_actif']
    search_fields = ['code', 'libelle']
    inlines = [RayonInline]

    @admin.display(description=_('Couleur'))
    def badge_couleur(self, obj):
        return format_html(
            '<span style="background:{};padding:4px 12px;border-radius:4px;">&nbsp;</span>',
            obj.couleur
        )


class EmplacementInline(admin.TabularInline):
    model = Emplacement
    extra = 0
    fields = ['code', 'niveau', 'colonne', 'statut']


@admin.register(Rayon)
class RayonAdmin(admin.ModelAdmin):
    list_display = ['code', 'libelle', 'zone', 'orientation', 'nombre_niveaux', 'nombre_colonnes', 'est_actif']
    list_filter = ['zone', 'orientation', 'est_actif']
    search_fields = ['code', 'libelle', 'zone__code']
    inlines = [EmplacementInline]


@admin.register(Emplacement)
class EmplacementAdmin(admin.ModelAdmin):
    list_display = ['code', 'rayon', 'niveau', 'colonne', 'badge_statut', 'type_produit_autorise']
    list_filter = ['statut', 'rayon__zone', 'type_produit_autorise']
    search_fields = ['code', 'notes']
    readonly_fields = ['date_creation']

    @admin.display(description=_('Statut'))
    def badge_statut(self, obj):
        couleurs = {
            'LIBRE': '#198754',
            'OCCUPE': '#0d6efd',
            'RESERVE': '#ffc107',
            'BLOQUE': '#dc3545',
            'QUARANTAINE': '#6f42c1',
        }
        couleur = couleurs.get(obj.statut, '#6c757d')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;">{}</span>',
            couleur, obj.get_statut_display()
        )


@admin.register(PlanMagasin)
class PlanMagasinAdmin(admin.ModelAdmin):
    list_display = ['nom', 'largeur_totale', 'hauteur_totale', 'echelle', 'est_actif']
