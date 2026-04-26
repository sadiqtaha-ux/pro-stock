"""
produits/forms.py
Formulaires pour la gestion des fournisseurs, unités et matières premières.
MediCare Industries - StockPro
"""

from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Fournisseur, UnitesMesure, MatierePremiere


class FournisseurForm(forms.ModelForm):
    class Meta:
        model = Fournisseur
        fields = ['nom', 'contact', 'email', 'telephone', 'adresse', 'ville', 'pays', 'statut', 'actif']
        widgets = {
            'adresse': forms.Textarea(attrs={'rows': 2, 'placeholder': _('Adresse complète...')}),
            'nom': forms.TextInput(attrs={'placeholder': _('Ex: PharmaCorp SARL')}),
        }


class UnitesMesureForm(forms.ModelForm):
    class Meta:
        model = UnitesMesure
        fields = ['nom', 'symbole']
        widgets = {
            'nom': forms.TextInput(attrs={'placeholder': _('Ex: Kilogramme')}),
            'symbole': forms.TextInput(attrs={'placeholder': _('Ex: kg')}),
        }


class MatierePremiereBaseForm(forms.ModelForm):
    """Formulaire de base pour la création/modification d'une matière première."""
    
    class Meta:
        model = MatierePremiere
        fields = [
            'reference', 'nom', 'description', 'categorie', 'unite', 
            'fournisseur_principal', 'prix_unitaire', 'stock_actuel', 
            'stock_minimum', 'stock_maximum', 'stock_securite',
            'methode_approvisionnement', 'point_commande', 'qec',
            'delai_livraison_jours', 'periode_reappro_jours', 'taux_rebut',
            'lot_minimum', 'multiple_lot',
            'zone_stockage', 'emplacement', 'actif'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'reference': forms.TextInput(attrs={'placeholder': _('Ex: API-001')}),
            'nom': forms.TextInput(attrs={'placeholder': _('Nom de la matière...')}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ajout de classes bootstrap
        for field_name, field in self.fields.items():
            if field_name != 'actif':
                field.widget.attrs.setdefault('class', 'form-control')
            else:
                field.widget.attrs.setdefault('class', 'form-check-input')

    def clean(self):
        cleaned_data = super().clean()
        unite = cleaned_data.get('unite')
        
        # Liste des champs de quantité à valider selon l'unité
        qty_fields = [
            'stock_actuel', 'stock_minimum', 'stock_maximum', 'stock_securite',
            'point_commande', 'qec', 'lot_minimum', 'multiple_lot'
        ]
        
        from .utils import validate_unit_quantity
        for field_name in qty_fields:
            value = cleaned_data.get(field_name)
            if value is not None:
                is_valid, error_msg = validate_unit_quantity(unite, value)
                if not is_valid:
                    self.add_error(field_name, error_msg)
        
        return cleaned_data


class MatierePremiereForm(MatierePremiereBaseForm):
    """Version complète du formulaire."""
    pass


class MatierePremiereStep1Form(forms.ModelForm):
    """Étape 1 : Informations de base."""
    class Meta:
        model = MatierePremiere
        fields = [
            'reference', 'nom', 'categorie', 'unite', 'fournisseur_principal',
            'prix_unitaire', 'stock_actuel', 'stock_minimum', 'stock_maximum', 
            'stock_securite', 'zone_stockage', 'emplacement', 'description', 'actif'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        unite = cleaned_data.get('unite')
        qty_fields = ['stock_actuel', 'stock_minimum', 'stock_maximum', 'stock_securite']
        
        from .utils import validate_unit_quantity
        for field_name in qty_fields:
            value = cleaned_data.get(field_name)
            if value is not None:
                is_valid, error_msg = validate_unit_quantity(unite, value)
                if not is_valid:
                    self.add_error(field_name, error_msg)
        return cleaned_data


class MatierePremiereStep2Form(forms.ModelForm):
    """Étape 2 : Paramètres de stock et réapprovisionnement."""
    class Meta:
        model = MatierePremiere
        fields = [
            'stock_actuel', 'stock_minimum', 'stock_maximum', 'stock_securite',
            'point_commande', 'qec', 'delai_livraison_jours', 
            'periode_reappro_jours', 'taux_rebut', 'lot_minimum', 'multiple_lot'
        ]


class MatierePremiereApproForm(forms.ModelForm):
    """Formulaire spécifique pour la méthode d'approvisionnement."""
    class Meta:
        model = MatierePremiere
        fields = ['methode_approvisionnement']
        widgets = {
            'methode_approvisionnement': forms.RadioSelect()
        }


class MatiereReapproFixeForm(forms.ModelForm):
    """Paramètres pour la méthode Réapprovisionnement Fixe (Q, T)."""
    class Meta:
        model = MatierePremiere
        fields = ['qec', 'periode_reappro_jours', 'delai_livraison_jours', 'stock_securite']
        widgets = {
            'qec': forms.NumberInput(attrs={'step': '0.0001'}),
        }

    def __init__(self, *args, **kwargs):
        self.unite = kwargs.pop('unite', None)
        super().__init__(*args, **kwargs)
        if not self.unite and self.instance and hasattr(self.instance, 'unite'):
            self.unite = self.instance.unite

    def clean(self):
        cleaned_data = super().clean()
        from .utils import validate_unit_quantity
        for f in ['qec', 'stock_securite']:
            val = cleaned_data.get(f)
            if val is not None:
                ok, err = validate_unit_quantity(self.unite, val)
                if not ok: self.add_error(f, err)
        return cleaned_data

class MatierePointCommandeForm(forms.ModelForm):
    """Paramètres pour la méthode Point de Commande (ROP)."""
    class Meta:
        model = MatierePremiere
        fields = ['point_commande', 'qec', 'delai_livraison_jours', 'stock_securite']
        widgets = {
            'point_commande': forms.NumberInput(attrs={'step': '0.0001'}),
            'qec': forms.NumberInput(attrs={'step': '0.0001'}),
        }

    def __init__(self, *args, **kwargs):
        self.unite = kwargs.pop('unite', None)
        super().__init__(*args, **kwargs)
        if not self.unite and self.instance and hasattr(self.instance, 'unite'):
            self.unite = self.instance.unite

    def clean(self):
        cleaned_data = super().clean()
        from .utils import validate_unit_quantity
        for f in ['point_commande', 'qec', 'stock_securite']:
            val = cleaned_data.get(f)
            if val is not None:
                ok, err = validate_unit_quantity(self.unite, val)
                if not ok: self.add_error(f, err)
        return cleaned_data

class MatiereRecompletementForm(forms.ModelForm):
    """Paramètres pour la méthode Récompletement (S, T)."""
    class Meta:
        model = MatierePremiere
        fields = ['stock_maximum', 'periode_reappro_jours', 'delai_livraison_jours', 'stock_securite']
        widgets = {
            'stock_maximum': forms.NumberInput(attrs={'step': '0.0001'}),
        }

    def __init__(self, *args, **kwargs):
        self.unite = kwargs.pop('unite', None)
        super().__init__(*args, **kwargs)
        if not self.unite and self.instance and hasattr(self.instance, 'unite'):
            self.unite = self.instance.unite

    def clean(self):
        cleaned_data = super().clean()
        from .utils import validate_unit_quantity
        for f in ['stock_maximum', 'stock_securite']:
            val = cleaned_data.get(f)
            if val is not None:
                ok, err = validate_unit_quantity(self.unite, val)
                if not ok: self.add_error(f, err)
        return cleaned_data

class MatiereMRPForm(forms.ModelForm):
    """Paramètres pour la méthode MRP."""
    class Meta:
        model = MatierePremiere
        fields = ['taux_rebut', 'lot_minimum', 'multiple_lot', 'delai_livraison_jours', 'periode_reappro_jours']
        widgets = {
            'taux_rebut': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'max': '99.99'}),
            'lot_minimum': forms.NumberInput(attrs={'step': '0.0001', 'min': '0'}),
            'multiple_lot': forms.NumberInput(attrs={'step': '0.0001', 'min': '1'}),
            'delai_livraison_jours': forms.NumberInput(attrs={'min': '0'}),
            'periode_reappro_jours': forms.NumberInput(attrs={'min': '1'}),
        }

    def __init__(self, *args, **kwargs):
        self.unite = kwargs.pop('unite', None)
        super().__init__(*args, **kwargs)
        # Si on n'a pas reçu l'unité mais qu'on a une instance, on la prend
        if not self.unite and self.instance and hasattr(self.instance, 'unite'):
            self.unite = self.instance.unite
            
        # Conversion du décimal en pourcentage pour l'affichage (ex: 0.02 -> 2.0)
        if self.instance and self.instance.taux_rebut:
            self.initial['taux_rebut'] = self.instance.taux_rebut * 100
        elif 'taux_rebut' in self.initial and self.initial['taux_rebut']:
            # Cas de la création avec données en session
            try:
                from decimal import Decimal
                val = Decimal(str(self.initial['taux_rebut']))
                if val < 1: # On suppose que si c'est < 1 en session c'est du décimal
                     self.initial['taux_rebut'] = val * 100
            except: pass

    def clean(self):
        cleaned_data = super().clean()
        from .utils import validate_unit_quantity
        for f in ['lot_minimum', 'multiple_lot']:
            val = cleaned_data.get(f)
            if val is not None:
                ok, err = validate_unit_quantity(self.unite, val)
                if not ok: self.add_error(f, err)
        return cleaned_data

    def clean_taux_rebut(self):
        val = self.cleaned_data.get('taux_rebut')
        if val is not None:
            if val < 0 or val >= 100:
                raise forms.ValidationError("Le taux doit être entre 0 et 100 %.")
            # Conversion du pourcentage en décimal pour le stockage (ex: 2.0 -> 0.02)
            return val / 100
        return 0

    def clean_multiple_lot(self):
        val = self.cleaned_data.get('multiple_lot')
        if val is not None and val < 1:
            raise forms.ValidationError("Le multiple de lot doit être au moins 1.")
        return val

    def clean_periode_reappro_jours(self):
        val = self.cleaned_data.get('periode_reappro_jours')
        if val is not None and val < 1:
            raise forms.ValidationError("La période de regroupement doit être au moins 1 jour.")
        return val

FORMULAIRES_PAR_METHODE = {
    'REAPPRO_FIXE': MatiereReapproFixeForm,
    'POINT_COMMANDE': MatierePointCommandeForm,
    'RECOMPLETEMENT': MatiereRecompletementForm,
    'MRP': MatiereMRPForm,
}

def get_formulaire_methode(methode):
    """Retourne la classe de formulaire correspondant à la méthode."""
    return FORMULAIRES_PAR_METHODE.get(methode, MatierePointCommandeForm)

class StockAjustementForm(forms.Form):
    """Formulaire pour ajuster manuellement le stock d'une MP."""
    quantite = forms.DecimalField(
        label=_("Nouvelle quantité en stock"),
        max_digits=14,
        decimal_places=4,
        min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'})
    )
    motif = forms.CharField(
        label=_("Motif de l'ajustement"),
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Ex: Inventaire de fin d\'année')})
    )


class ProduitFiniForm(forms.ModelForm):
    """Formulaire pour les produits finis."""
    class Meta:
        from .models import ProduitFini
        model = ProduitFini
        fields = [
            'reference', 'nom', 'description', 'categorie', 'unite',
            'stock_actuel', 'stock_minimum', 'stock_maximum', 'prix_unitaire',
            'statut', 'zone_stockage', 'emplacement', 'numero_lot', 'date_peremption', 'actif'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'date_peremption': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name != 'actif':
                field.widget.attrs.setdefault('class', 'form-control')
            else:
                field.widget.attrs.setdefault('class', 'form-check-input')

    def clean(self):
        cleaned_data = super().clean()
        unite = cleaned_data.get('unite')
        
        # Liste des champs de quantité à valider selon l'unité
        qty_fields = ['stock_actuel', 'stock_minimum', 'stock_maximum']
        
        from .utils import validate_unit_quantity
        for field_name in qty_fields:
            value = cleaned_data.get(field_name)
            if value is not None:
                is_valid, error_msg = validate_unit_quantity(unite, value)
                if not is_valid:
                    self.add_error(field_name, error_msg)
        
        return cleaned_data


class NomenclatureForm(forms.ModelForm):
    class Meta:
        from .models import Nomenclature
        model = Nomenclature
        fields = ['nom', 'version', 'actif']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name != 'actif':
                field.widget.attrs.setdefault('class', 'form-control')
            else:
                field.widget.attrs.setdefault('class', 'form-check-input')


class LigneNomenclatureForm(forms.ModelForm):
    """Formulaire pour ajouter un composant à un produit fini."""
    class Meta:
        from .models import LigneNomenclature
        model = LigneNomenclature
        fields = ['matiere', 'quantite_par_unite', 'taux_perte', 'obligatoire', 'ordre_affichage']
        widgets = {
            'quantite_par_unite': forms.NumberInput(attrs={'step': '0.000001'}),
            'taux_perte': forms.NumberInput(attrs={'step': '0.0001'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name != 'obligatoire':
                field.widget.attrs.setdefault('class', 'form-control')
            else:
                field.widget.attrs.setdefault('class', 'form-check-input')
