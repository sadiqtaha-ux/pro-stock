"""approvisionnement/forms.py"""
from django import forms
from .models import BonCommande, PlanMRP


class BonCommandeForm(forms.ModelForm):
    class Meta:
        model  = BonCommande
        fields = [
            "matiere", "fournisseur", "quantite_commandee", "prix_unitaire",
            "methode_declenchement", "statut",
            "date_reception_prevue", "notes",
        ]
        widgets = {
            "date_reception_prevue": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }


class PlanMRPForm(forms.ModelForm):
    class Meta:
        model  = PlanMRP
        fields = [
            "matiere", "periode", "besoin_brut", "stock_debut_periode",
            "besoin_net", "quantite_proposee", "stock_fin_periode", "statut",
        ]
        widgets = {
            "periode": forms.DateInput(attrs={"type": "date"}),
        }
