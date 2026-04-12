"""mouvements/forms.py"""
from django import forms
from .models import MouvementStock


class MouvementStockForm(forms.ModelForm):
    class Meta:
        model  = MouvementStock
        fields = [
            "matiere", "type_mouvement", "quantite", "quantite_avant",
            "motif", "numero_lot", "date_peremption", "bon_commande",
        ]
        widgets = {
            "date_peremption": forms.DateInput(attrs={"type": "date"}),
            "motif": forms.Textarea(attrs={"rows": 2}),
        }
