"""produits/forms.py"""
from django import forms
from .models import Fournisseur, UnitesMesure, MatierePremiere


class MatierePremiereForm(forms.ModelForm):
    class Meta:
        model  = MatierePremiere
        fields = [
            "reference", "nom", "description", "categorie",
            "unite", "fournisseur_principal", "prix_unitaire",
            "stock_actuel", "stock_minimum", "stock_maximum", "stock_securite",
            "methode_approvisionnement", "point_commande", "qec",
            "delai_livraison_jours", "periode_reappro_jours", "taux_rebut",
            "zone_stockage", "emplacement", "actif",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }


class FournisseurForm(forms.ModelForm):
    class Meta:
        model  = Fournisseur
        fields = ["nom", "contact", "email", "telephone", "adresse", "ville", "pays", "actif"]
        widgets = {
            "adresse": forms.Textarea(attrs={"rows": 2}),
        }


class UnitesMesureForm(forms.ModelForm):
    class Meta:
        model  = UnitesMesure
        fields = ["nom", "symbole"]
