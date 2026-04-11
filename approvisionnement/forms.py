"""
App Approvisionnement - Formulaires
"""

from django import forms
from django.utils.translation import gettext_lazy as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Field, Fieldset

from .models import CommandeAchat, LigneCommandeAchat, SuggestionAppro, ParametreAppro, PlanMRP


class CommandeAchatForm(forms.ModelForm):
    class Meta:
        model = CommandeAchat
        fields = [
            'fournisseur', 'type_commande', 'date_commande',
            'date_livraison_prevue', 'conditions_paiement', 'notes'
        ]
        widgets = {
            'fournisseur': forms.Select(attrs={'class': 'form-select', 'id': 'id_fournisseur_commande'}),
            'type_commande': forms.Select(attrs={'class': 'form-select'}),
            'date_commande': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'date_livraison_prevue': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'conditions_paiement': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(Column('fournisseur', css_class='col-md-8'), Column('type_commande', css_class='col-md-4')),
            Row(Column('date_commande', css_class='col-md-6'), Column('date_livraison_prevue', css_class='col-md-6')),
            'conditions_paiement',
            'notes',
            Submit('submit', _('Enregistrer la commande'), css_class='btn btn-primary'),
        )


class LigneCommandeAchatForm(forms.ModelForm):
    class Meta:
        model = LigneCommandeAchat
        fields = ['produit', 'quantite_commandee', 'unite', 'prix_unitaire_ht', 'remise', 'tva']
        widgets = {
            'produit': forms.Select(attrs={'class': 'form-select', 'id': 'id_produit_ligne'}),
            'unite': forms.Select(attrs={'class': 'form-select'}),
            'quantite_commandee': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'prix_unitaire_ht': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
            'remise': forms.NumberInput(attrs={'class': 'form-control'}),
            'tva': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class ParametreApproForm(forms.ModelForm):
    class Meta:
        model = ParametreAppro
        fields = [
            'methode', 'consommation_journaliere_moyenne', 'ecart_type_consommation',
            'delai_reappro_jours', 'niveau_service', 'cout_possession', 'cout_passation',
            'quantite_commande_fixe', 'periodicite_commande',
            'periode_revision', 'stock_cible',
            'nomenclature_coefficient', 'lot_multiple', 'horizon_planification',
        ]
        widgets = {
            'methode': forms.Select(attrs={'class': 'form-select', 'id': 'id_methode_param'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, forms.Select):
                field.widget.attrs.update({'class': 'form-control'})

        self.helper = FormHelper()
        self.helper.layout = Layout(
            'methode',
            Fieldset(_('Paramètres communs'),
                Row(Column('consommation_journaliere_moyenne', css_class='col-md-6'), Column('ecart_type_consommation', css_class='col-md-6')),
                Row(Column('delai_reappro_jours', css_class='col-md-4'), Column('niveau_service', css_class='col-md-4'), Column('cout_possession', css_class='col-md-4')),
                'cout_passation',
            ),
            Fieldset(_('[FIXE] Réappro Fixe'),
                Row(Column('quantite_commande_fixe', css_class='col-md-6'), Column('periodicite_commande', css_class='col-md-6')),
            ),
            Fieldset(_('[S,T] Récompletement'),
                Row(Column('stock_cible', css_class='col-md-6'), Column('periode_revision', css_class='col-md-6')),
            ),
            Fieldset(_('[MRP] Planification'),
                Row(Column('nomenclature_coefficient', css_class='col-md-4'), Column('lot_multiple', css_class='col-md-4'), Column('horizon_planification', css_class='col-md-4')),
            ),
            Submit('submit', _('Enregistrer les paramètres'), css_class='btn btn-success'),
        )


class PlanMRPForm(forms.ModelForm):
    class Meta:
        model = PlanMRP
        fields = ['description', 'date_debut', 'date_fin', 'horizon_semaines', 'notes']
        widgets = {
            'date_debut': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'date_fin': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'horizon_semaines': forms.NumberInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }


class SuggestionApproForm(forms.ModelForm):
    class Meta:
        model = SuggestionAppro
        fields = ['statut']
        widgets = {
            'statut': forms.Select(attrs={'class': 'form-select'}),
        }
