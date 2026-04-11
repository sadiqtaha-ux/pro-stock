"""
App Dashboard - Formulaires
"""

from django import forms
from django.utils.translation import gettext_lazy as _
from .models import RapportSauvegarde


class RapportForm(forms.ModelForm):
    class Meta:
        model = RapportSauvegarde
        fields = ['nom', 'type_rapport', 'periode_debut', 'periode_fin']
        widgets = {
            'type_rapport': forms.Select(attrs={'class': 'form-select', 'id': 'id_type_rapport'}),
            'periode_debut': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'periode_fin': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
        }


class FiltreRapportStockForm(forms.Form):
    """Filtres pour la génération du rapport de stock."""
    categorie = forms.ChoiceField(required=False, label=_('Catégorie'), widget=forms.Select(attrs={'class': 'form-select'}))
    statut_stock = forms.ChoiceField(
        choices=[('', _('Tous')), ('rupture', _('Rupture')), ('alerte', _('Alerte')), ('normal', _('Normal'))],
        required=False,
        label=_('Statut stock'),
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_statut_stock_rapport'}),
    )
    classe_abc = forms.ChoiceField(
        choices=[('', _('Toutes')), ('A', 'A'), ('B', 'B'), ('C', 'C')],
        required=False,
        label=_('Classe ABC'),
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
