"""
App Dashboard - Administration
"""

from django.contrib import admin
from .models import RapportSauvegarde, KPISnapshot


@admin.register(RapportSauvegarde)
class RapportSauvegardeAdmin(admin.ModelAdmin):
    list_display = ['nom', 'type_rapport', 'genere_par', 'date_generation', 'periode_debut', 'periode_fin']
    list_filter = ['type_rapport', 'date_generation']
    search_fields = ['nom']
    readonly_fields = ['date_creation', 'date_generation']


@admin.register(KPISnapshot)
class KPISnapshotAdmin(admin.ModelAdmin):
    list_display = ['date', 'nb_references_actives', 'nb_ruptures', 'nb_alertes', 'valeur_stock_total', 'taux_service']
    ordering = ['-date']
    date_hierarchy = 'date'
    readonly_fields = [f.name for f in KPISnapshot._meta.fields]

    def has_add_permission(self, request):
        return False
