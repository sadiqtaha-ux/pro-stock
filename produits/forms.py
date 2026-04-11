"""
App Produits - Formulaires
"""

from django import forms
from django.utils.translation import gettext_lazy as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Field, Fieldset, HTML

from .models import Produit, Fournisseur, CategorieProduit, UniteMesure, LotProduit


class ProduitForm(forms.ModelForm):
    """Formulaire de création/modification d'un produit."""

    class Meta:
        model = Produit
        fields = [
            'code', 'designation', 'description', 'photo', 'statut',
            'categorie', 'classe_abc', 'fournisseur_principal',
            'unite_stock', 'unite_achat', 'coefficient_conversion',
            'stock_minimum', 'stock_maximum', 'stock_securite',
            'point_commande', 'quantite_economique',
            'prix_unitaire_achat', 'prix_unitaire_revient', 'tva',
            'type_stockage', 'duree_conservation',
            'methode_appro', 'delai_reappro', 'periodicite_reappro',
            'emplacement',
        ]
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_code_produit'}),
            'designation': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'categorie': forms.Select(attrs={'class': 'form-select'}),
            'classe_abc': forms.Select(attrs={'class': 'form-select'}),
            'fournisseur_principal': forms.Select(attrs={'class': 'form-select'}),
            'unite_stock': forms.Select(attrs={'class': 'form-select'}),
            'unite_achat': forms.Select(attrs={'class': 'form-select'}),
            'methode_appro': forms.Select(attrs={'class': 'form-select', 'id': 'id_methode_appro'}),
            'statut': forms.Select(attrs={'class': 'form-select'}),
            'type_stockage': forms.Select(attrs={'class': 'form-select'}),
            'emplacement': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Rendre tous les champs numériques avec class form-control
        numeric_fields = [
            'coefficient_conversion', 'stock_minimum', 'stock_maximum',
            'stock_securite', 'point_commande', 'quantite_economique',
            'prix_unitaire_achat', 'prix_unitaire_revient', 'tva',
            'duree_conservation', 'delai_reappro', 'periodicite_reappro',
        ]
        for field_name in numeric_fields:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs.update({'class': 'form-control'})

        self.helper = FormHelper()
        self.helper.form_enctype = 'multipart/form-data'
        self.helper.layout = Layout(
            Fieldset(_('Identification'),
                Row(Column('code', css_class='col-md-4'), Column('designation', css_class='col-md-8')),
                'description', 'photo',
            ),
            Fieldset(_('Classification'),
                Row(
                    Column('categorie', css_class='col-md-4'),
                    Column('classe_abc', css_class='col-md-4'),
                    Column('statut', css_class='col-md-4'),
                ),
                Row(
                    Column('fournisseur_principal', css_class='col-md-6'),
                    Column('emplacement', css_class='col-md-6'),
                ),
            ),
            Fieldset(_('Unités'),
                Row(
                    Column('unite_stock', css_class='col-md-4'),
                    Column('unite_achat', css_class='col-md-4'),
                    Column('coefficient_conversion', css_class='col-md-4'),
                ),
            ),
            Fieldset(_('Paramètres de stock'),
                Row(
                    Column('stock_minimum', css_class='col-md-4'),
                    Column('stock_securite', css_class='col-md-4'),
                    Column('stock_maximum', css_class='col-md-4'),
                ),
                Row(
                    Column('point_commande', css_class='col-md-6'),
                    Column('quantite_economique', css_class='col-md-6'),
                ),
            ),
            Fieldset(_('Tarification'),
                Row(
                    Column('prix_unitaire_achat', css_class='col-md-4'),
                    Column('prix_unitaire_revient', css_class='col-md-4'),
                    Column('tva', css_class='col-md-4'),
                ),
            ),
            Fieldset(_('Stockage & Approvisionnement'),
                Row(
                    Column('type_stockage', css_class='col-md-4'),
                    Column('duree_conservation', css_class='col-md-4'),
                ),
                Row(
                    Column('methode_appro', css_class='col-md-4'),
                    Column('delai_reappro', css_class='col-md-4'),
                    Column('periodicite_reappro', css_class='col-md-4'),
                ),
            ),
            Submit('submit', _('Enregistrer le produit'), css_class='btn btn-primary btn-lg mt-3'),
        )


class FournisseurForm(forms.ModelForm):
    """Formulaire fournisseur."""

    class Meta:
        model = Fournisseur
        fields = [
            'code', 'raison_sociale', 'nom_commercial', 'statut',
            'adresse', 'ville', 'code_postal', 'pays',
            'telephone', 'fax', 'email', 'site_web',
            'contact_nom', 'contact_telephone', 'contact_email', 'contact_poste',
            'ice', 'if_numero', 'rc', 'delai_livraison_moyen',
            'conditions_paiement', 'remise_habituelle', 'note_evaluation', 'notes',
        ]
        widgets = {
            'adresse': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 3}),
            'statut': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, (forms.Select, forms.Textarea)):
                field.widget.attrs.update({'class': 'form-control'})
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({'class': 'form-control'})


class CategorieProduitForm(forms.ModelForm):
    class Meta:
        model = CategorieProduit
        fields = ['code', 'libelle', 'description', 'parent', 'couleur', 'icone', 'est_actif']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'parent': forms.Select(attrs={'class': 'form-select'}),
            'couleur': forms.TextInput(attrs={'type': 'color', 'class': 'form-control form-control-color'}),
        }


class UniteMesureForm(forms.ModelForm):
    class Meta:
        model = UniteMesure
        fields = ['code', 'libelle', 'libelle_pluriel', 'categorie', 'est_actif']
        widgets = {
            'categorie': forms.Select(attrs={'class': 'form-select'}),
        }


class LotProduitForm(forms.ModelForm):
    class Meta:
        model = LotProduit
        fields = [
            'produit', 'numero_lot', 'date_fabrication', 'date_peremption',
            'quantite_initiale', 'statut', 'origine', 'certificat_analyse', 'notes',
        ]
        widgets = {
            'date_fabrication': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'date_peremption': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'produit': forms.Select(attrs={'class': 'form-select'}),
            'statut': forms.Select(attrs={'class': 'form-select'}),
        }


class RechercheProduitsForm(forms.Form):
    """Formulaire de recherche avancée des produits."""
    q = forms.CharField(
        required=False,
        label=_('Recherche'),
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Code, désignation...')}),
    )
    categorie = forms.ModelChoiceField(
        queryset=CategorieProduit.objects.filter(est_actif=True),
        required=False,
        label=_('Catégorie'),
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    classe_abc = forms.ChoiceField(
        choices=[('', _('Toutes les classes'))] + Produit.ClasseABC.choices,
        required=False,
        label=_('Classe ABC'),
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    statut_stock = forms.ChoiceField(
        choices=[
            ('', _('Tous')),
            ('alerte', _('En alerte')),
            ('rupture', _('En rupture')),
            ('surstock', _('En surstock')),
            ('normal', _('Normal')),
        ],
        required=False,
        label=_('Statut stock'),
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
