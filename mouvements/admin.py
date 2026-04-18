"""mouvements/admin.py"""
from django.contrib import admin
from .models import MouvementStock


@admin.register(MouvementStock)
class MouvementStockAdmin(admin.ModelAdmin):
    list_display   = (
        "date_mouvement", "matiere", "type_mouvement",
        "quantite", "quantite_avant", "quantite_apres",
        "numero_lot", "operateur"
    )
    list_filter    = ("type_mouvement",)
    search_fields  = ("matiere__nom", "matiere__reference", "numero_lot", "motif")
    readonly_fields = ("date_mouvement", "quantite_apres")
    date_hierarchy  = "date_mouvement"
    fieldsets = (
        ("Mouvement", {
            "fields": ("matiere", "type_mouvement", "quantite", "quantite_avant", "quantite_apres")
        }),
        ("Traçabilité lot", {
            "fields": ("numero_lot", "date_peremption", "motif")
        }),
        ("Opérateur & commande", {
            "fields": ("operateur", "bon_commande", "date_mouvement"),
            "classes": ("collapse",)
        }),
    )
