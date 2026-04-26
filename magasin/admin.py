"""
App Magasin - Administration
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.db.models import Count, Q

from .models import ZoneStockage, Rayon, Emplacement, PlanMagasin, NiveauRayon, AffectationStock


class RayonInline(admin.TabularInline):
    model = Rayon
    extra = 1
    fields = ['code', 'libelle', 'orientation', 'nombre_niveaux', 'nombre_colonnes']


class NiveauRayonInline(admin.TabularInline):
    model = NiveauRayon
    extra = 1
    fields = ['numero', 'libelle', 'capacite_max', 'actif']


@admin.register(ZoneStockage)
class ZoneStockageAdmin(admin.ModelAdmin):
    list_display = ['code', 'nom', 'libelle', 'type_zone', 'badge_couleur', 'ordre', 'actif']
    list_filter = ['type_zone', 'actif']
    search_fields = ['code', 'nom', 'libelle']
    inlines = [RayonInline]
    ordering = ['ordre', 'code']

    @admin.display(description=_('Couleur'))
    def badge_couleur(self, obj):
        return format_html(
            '<span style="background:{};padding:4px 12px;border-radius:4px;border:1px solid #ddd;">&nbsp;</span>',
            obj.couleur
        )


class EmplacementInline(admin.TabularInline):
    model = Emplacement
    extra = 0
    fields = ['code', 'niveau', 'colonne', 'statut']


@admin.register(Rayon)
class RayonAdmin(admin.ModelAdmin):
    list_display = ['code', 'nom', 'zone', 'type_stock', 'statut', 'badge_couleur', 'actif']
    list_filter = ['zone', 'type_stock', 'statut', 'actif']
    search_fields = ['code', 'nom', 'libelle', 'zone__code']
    inlines = [NiveauRayonInline, EmplacementInline]

    @admin.display(description=_('Couleur'))
    def badge_couleur(self, obj):
        return format_html(
            '<span style="background:{};padding:4px 12px;border-radius:4px;border:1px solid #ddd;">&nbsp;</span>',
            obj.couleur
        )


@admin.register(NiveauRayon)
class NiveauRayonAdmin(admin.ModelAdmin):
    list_display = ['rayon', 'numero', 'libelle', 'capacite_max', 'actif']
    list_filter = ['rayon__zone', 'actif']
    search_fields = ['rayon__code', 'libelle']


@admin.register(AffectationStock)
class AffectationStockAdmin(admin.ModelAdmin):
    list_display = ['niveau', 'article_display', 'quantite_affectee', 'date_affectation', 'actif']
    list_filter = ['actif', 'date_affectation', 'niveau__rayon__zone']
    search_fields = ['matiere_premiere__nom', 'produit_fini__nom', 'niveau__rayon__code']

    @admin.display(description=_('Article'))
    def article_display(self, obj):
        if obj.matiere_premiere:
            return format_html('<span class="badge bg-info">MP</span> {}', obj.matiere_premiere)
        if obj.produit_fini:
            return format_html('<span class="badge bg-success">PF</span> {}', obj.produit_fini)
        return "—"


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
