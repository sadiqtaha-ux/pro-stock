"""
App Mouvements - Formulaires
"""

from django import forms
from django.utils.translation import gettext_lazy as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Field, Fieldset

from .models import MouvementStock, BonEntree, BonSortie, Inventaire, LigneInventaire
from produits.models import Produit, Fournisseur


class MouvementStockForm(forms.ModelForm):
    class Meta:
        model = MouvementStock
        fields = [
            'type_mouvement', 'produit', 'lot', 'quantite', 'unite',
            'prix_unitaire', 'date_mouvement', 'reference_document',
            'fournisseur', 'emplacement_source', 'emplacement_destination', 'motif',
        ]
        widgets = {
            'type_mouvement': forms.Select(attrs={'class': 'form-select', 'id': 'id_type_mouvement'}),
            'produit': forms.Select(attrs={'class': 'form-select', 'id': 'id_produit_mvt'}),
            'lot': forms.Select(attrs={'class': 'form-select'}),
            'unite': forms.Select(attrs={'class': 'form-select'}),
            'fournisseur': forms.Select(attrs={'class': 'form-select'}),
            'date_mouvement': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'motif': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'emplacement_source': forms.Select(attrs={'class': 'form-select'}),
            'emplacement_destination': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ['quantite', 'prix_unitaire', 'reference_document']:
            self.fields[field_name].widget.attrs.update({'class': 'form-control'})


class BonEntreeForm(forms.ModelForm):
    class Meta:
        model = BonEntree
        fields = ['fournisseur', 'commande', 'date_reception', 'reference_fournisseur', 'notes']
        widgets = {
            'fournisseur': forms.Select(attrs={'class': 'form-select', 'id': 'id_fournisseur_entree'}),
            'commande': forms.Select(attrs={'class': 'form-select'}),
            'date_reception': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'reference_fournisseur': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(Column('fournisseur', css_class='col-md-6'), Column('commande', css_class='col-md-6')),
            Row(Column('date_reception', css_class='col-md-6'), Column('reference_fournisseur', css_class='col-md-6')),
            'notes',
            Submit('submit', _("Créer le bon d'entrée"), css_class='btn btn-success'),
        )


class BonSortieForm(forms.ModelForm):
    class Meta:
        model = BonSortie
        fields = ['service_demandeur', 'date_livraison_souhaitee', 'motif', 'notes']
        widgets = {
            'service_demandeur': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_service_demandeur'}),
            'date_livraison_souhaitee': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'motif': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(Column('service_demandeur', css_class='col-md-6'), Column('date_livraison_souhaitee', css_class='col-md-6')),
            'motif',
            'notes',
            Submit('submit', _('Créer le bon de sortie'), css_class='btn btn-warning'),
        )


class InventaireForm(forms.ModelForm):
    class Meta:
        model = Inventaire
        fields = ['date_debut', 'type_inventaire', 'observations']
        widgets = {
            'date_debut': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'type_inventaire': forms.Select(attrs={'class': 'form-select', 'id': 'id_type_inventaire'}),
            'observations': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }


class LigneInventaireForm(forms.ModelForm):
    class Meta:
        model = LigneInventaire
        fields = ['produit', 'lot', 'quantite_theorique', 'quantite_comptee', 'observations']
        widgets = {
            'produit': forms.Select(attrs={'class': 'form-select'}),
            'lot': forms.Select(attrs={'class': 'form-select'}),
            'quantite_theorique': forms.NumberInput(attrs={'class': 'form-control'}),
            'quantite_comptee': forms.NumberInput(attrs={'class': 'form-control'}),
            'observations': forms.TextInput(attrs={'class': 'form-control'}),
        }
