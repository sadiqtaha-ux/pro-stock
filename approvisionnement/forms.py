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

    def clean(self):
        cleaned_data = super().clean()
        matiere = cleaned_data.get('matiere')
        quantite = cleaned_data.get('quantite_commandee')
        
        if matiere and quantite is not None:
            from produits.utils import validate_unit_quantity
            ok, err = validate_unit_quantity(matiere.unite, quantite)
            if not ok:
                self.add_error('quantite_commandee', err)
        return cleaned_data


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

    def clean(self):
        cleaned_data = super().clean()
        matiere = cleaned_data.get('matiere')
        
        from produits.utils import validate_unit_quantity
        for f in ['besoin_brut', 'besoin_net', 'quantite_proposee']:
            val = cleaned_data.get(f)
            if val is not None and matiere:
                ok, err = validate_unit_quantity(matiere.unite, val)
                if not ok: self.add_error(f, err)
        return cleaned_data
