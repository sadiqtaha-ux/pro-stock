"""mouvements/forms.py"""
from django import forms
from django.db import transaction
from django.core.exceptions import ValidationError
from .models import MouvementStock


class MouvementStockForm(forms.ModelForm):
    type_stock = forms.ChoiceField(
        choices=MouvementStock.TYPE_STOCK_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model  = MouvementStock
        fields = [
            "type_stock", "matiere", "produit_fini", 
            "type_mouvement", "quantite", "quantite_avant",
            "motif", "numero_lot", "date_peremption", "bon_commande",
        ]
        widgets = {
            "date_peremption": forms.DateInput(attrs={"type": "date"}),
            "motif": forms.Textarea(attrs={"rows": 2}),
        }

    def clean(self):
        cleaned_data = super().clean()
        type_stock = cleaned_data.get('type_stock')
        matiere = cleaned_data.get('matiere')
        produit_fini = cleaned_data.get('produit_fini')
        quantite = cleaned_data.get('quantite')
        type_mouvement = cleaned_data.get('type_mouvement')

        if not type_stock:
            self.add_error('type_stock', "Veuillez sélectionner le type de stock.")
            return cleaned_data

        if type_stock == 'MP' and not matiere:
            self.add_error('matiere', "Veuillez sélectionner une matière première.")
        if type_stock == 'PF' and not produit_fini:
            self.add_error('produit_fini', "Veuillez sélectionner un produit fini.")

        if type_stock == 'MP' and produit_fini:
            cleaned_data['produit_fini'] = None
            produit_fini = None
        if type_stock == 'PF' and matiere:
            cleaned_data['matiere'] = None
            matiere = None

        article = matiere if type_stock == 'MP' else produit_fini

        if article and quantite is not None:
            if quantite <= 0:
                self.add_error('quantite', "La quantité doit être strictement positive.")

            from produits.utils import validate_unit_quantity
            ok, err = validate_unit_quantity(article.unite, quantite)
            if not ok:
                self.add_error('quantite', err)

            if type_mouvement == MouvementStock.TypeMouvement.SORTIE:
                if quantite > article.stock_actuel:
                    self.add_error('quantite', f"Stock insuffisant. Stock actuel : {article.stock_actuel}.")

        return cleaned_data

    def save(self, commit=True):
        """
        Délègue la sauvegarde au modèle. La logique de mise à jour du stock
        est désormais centralisée dans MouvementStock.save().
        """
        return super().save(commit=commit)
