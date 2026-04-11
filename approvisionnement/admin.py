"""approvisionnement/admin.py"""
from django.contrib import admin
from .models import BonCommande, PlanMRP


@admin.register(BonCommande)
class BonCommandeAdmin(admin.ModelAdmin):
    list_display  = ("reference", "matiere", "fournisseur", "quantite_commandee",
                     "montant_total", "methode_declenchement", "statut", "date_creation")
    list_filter   = ("statut", "methode_declenchement")
    search_fields = ("reference", "matiere__nom", "fournisseur__nom")
    readonly_fields = ("reference", "montant_total", "date_creation")
    fieldsets = (
        ("Identification", {
            "fields": ("reference", "matiere", "fournisseur", "statut")
        }),
        ("Quantités & prix", {
            "fields": ("quantite_commandee", "prix_unitaire", "montant_total")
        }),
        ("Déclenchement", {
            "fields": ("methode_declenchement",)
        }),
        ("Dates", {
            "fields": ("date_creation", "date_envoi", "date_reception_prevue", "date_reception_reelle")
        }),
        ("Autres", {
            "fields": ("cree_par", "notes"),
            "classes": ("collapse",)
        }),
    )


@admin.register(PlanMRP)
class PlanMRPAdmin(admin.ModelAdmin):
    list_display = ("matiere", "periode", "besoin_brut", "besoin_net",
                    "quantite_proposee", "stock_fin_periode", "statut")
    list_filter  = ("statut",)
    search_fields = ("matiere__nom", "matiere__reference")
    date_hierarchy = "periode"
