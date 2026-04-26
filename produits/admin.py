"""produits/admin.py"""
from django.contrib import admin
from .models import Fournisseur, UnitesMesure, MatierePremiere, ProduitFini, Nomenclature, LigneNomenclature


@admin.register(Fournisseur)
class FournisseurAdmin(admin.ModelAdmin):
    list_display  = ("nom", "contact", "email", "telephone", "ville", "pays", "actif")
    list_filter   = ("actif", "pays")
    search_fields = ("nom", "contact", "email", "ville")
    list_editable = ("actif",)


@admin.register(UnitesMesure)
class UnitesMesureAdmin(admin.ModelAdmin):
    list_display  = ("nom", "symbole")
    search_fields = ("nom", "symbole")


@admin.register(MatierePremiere)
class MatierePremiereAdmin(admin.ModelAdmin):
    list_display  = (
        "reference", "nom", "categorie",
        "stock_actuel", "stock_minimum",
        "methode_approvisionnement", "zone_stockage", "emplacement", "actif"
    )
    list_filter   = ("categorie", "methode_approvisionnement", "zone_stockage", "actif")
    search_fields = ("reference", "nom")
    list_editable = ("actif",)
    readonly_fields = ("date_creation", "date_modification")
    fieldsets = (
        ("Identification", {
            "fields": ("reference", "nom", "description", "categorie", "unite", "actif")
        }),
        ("Fournisseur", {
            "fields": ("fournisseur_principal", "prix_unitaire")
        }),
        ("Stock", {
            "fields": ("stock_actuel", "stock_minimum", "stock_maximum", "stock_securite")
        }),
        ("Approvisionnement", {
            "fields": (
                "methode_approvisionnement", "point_commande", "qec",
                "delai_livraison_jours", "periode_reappro_jours", "taux_rebut"
            )
        }),
        ("Stockage physique", {
            "fields": ("zone_stockage", "emplacement")
        }),
        ("Métadonnées", {
            "fields": ("date_creation", "date_modification"),
            "classes": ("collapse",)
        }),
    )

@admin.register(ProduitFini)
class ProduitFiniAdmin(admin.ModelAdmin):
    list_display = ("reference", "nom", "categorie", "stock_actuel", "actif")
    list_filter = ("categorie", "actif")
    search_fields = ("reference", "nom")

@admin.register(Nomenclature)
class NomenclatureAdmin(admin.ModelAdmin):
    list_display = ("produit_fini", "nom", "version", "actif", "date_creation")
    list_filter = ("actif",)
    search_fields = ("produit_fini__nom", "nom")

@admin.register(LigneNomenclature)
class LigneNomenclatureAdmin(admin.ModelAdmin):
    list_display = ("nomenclature", "matiere", "quantite_par_unite", "obligatoire", "ordre_affichage")
    list_filter = ("obligatoire",)
    search_fields = ("nomenclature__produit_fini__nom", "matiere__nom")
