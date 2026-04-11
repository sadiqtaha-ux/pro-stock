"""
App Magasin - Formulaires
"""

from django import forms
from django.utils.translation import gettext_lazy as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column

from .models import ZoneStockage, Rayon, Emplacement


class ZoneStockageForm(forms.ModelForm):
    class Meta:
        model = ZoneStockage
        fields = ['code', 'libelle', 'type_zone', 'description', 'couleur',
                  'position_x', 'position_y', 'largeur', 'hauteur', 'capacite_totale']
        widgets = {
            'type_zone': forms.Select(attrs={'class': 'form-select', 'id': 'id_type_zone'}),
            'couleur': forms.TextInput(attrs={'type': 'color', 'class': 'form-control form-control-color'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ['code', 'libelle', 'position_x', 'position_y', 'largeur', 'hauteur', 'capacite_totale']:
            self.fields[field_name].widget.attrs.update({'class': 'form-control'})
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(Column('code', css_class='col-md-3'), Column('libelle', css_class='col-md-6'), Column('type_zone', css_class='col-md-3')),
            'description',
            Row(Column('couleur', css_class='col-md-2'), Column('capacite_totale', css_class='col-md-4')),
            Row(Column('position_x', css_class='col-md-3'), Column('position_y', css_class='col-md-3'),
                Column('largeur', css_class='col-md-3'), Column('hauteur', css_class='col-md-3')),
            Submit('submit', _('Enregistrer la zone'), css_class='btn btn-success'),
        )


class RayonForm(forms.ModelForm):
    class Meta:
        model = Rayon
        fields = ['zone', 'code', 'libelle', 'orientation', 'nombre_niveaux', 'nombre_colonnes',
                  'position_x', 'position_y', 'largeur', 'hauteur']
        widgets = {
            'zone': forms.Select(attrs={'class': 'form-select', 'id': 'id_zone_rayon'}),
            'orientation': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in ['code', 'libelle', 'nombre_niveaux', 'nombre_colonnes',
                      'position_x', 'position_y', 'largeur', 'hauteur']:
            self.fields[field].widget.attrs.update({'class': 'form-control'})


class EmplacementForm(forms.ModelForm):
    class Meta:
        model = Emplacement
        fields = ['rayon', 'code', 'niveau', 'colonne', 'statut',
                  'capacite_poids_max', 'capacite_volume_max', 'type_produit_autorise', 'notes']
        widgets = {
            'rayon': forms.Select(attrs={'class': 'form-select', 'id': 'id_rayon_emp'}),
            'statut': forms.Select(attrs={'class': 'form-select'}),
            'type_produit_autorise': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in ['code', 'niveau', 'colonne', 'capacite_poids_max', 'capacite_volume_max']:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(Column('rayon', css_class='col-md-6'), Column('statut', css_class='col-md-6')),
            Row(Column('code', css_class='col-md-4'), Column('niveau', css_class='col-md-4'), Column('colonne', css_class='col-md-4')),
            Row(Column('capacite_poids_max', css_class='col-md-6'), Column('capacite_volume_max', css_class='col-md-6')),
            'type_produit_autorise',
            'notes',
            Submit('submit', _('Enregistrer l\'emplacement'), css_class='btn btn-success'),
        )
