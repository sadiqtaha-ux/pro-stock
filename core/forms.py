"""
App Core - Formulaires
Connexion, profil utilisateur, gestion des utilisateurs
"""

from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, UserCreationForm
from django.utils.translation import gettext_lazy as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Field, HTML, Div

from .models import Utilisateur


# ============================================================
# FORMULAIRE DE CONNEXION
# ============================================================

class ConnexionForm(AuthenticationForm):
    """Formulaire de connexion personnalisé."""

    username = forms.CharField(
        label=_('Identifiant'),
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': _('Votre identifiant'),
            'autofocus': True,
            'id': 'id_username_login',
        }),
    )
    password = forms.CharField(
        label=_('Mot de passe'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': _('Votre mot de passe'),
            'id': 'id_password_login',
        }),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_id = 'form-connexion'
        self.helper.layout = Layout(
            Field('username', css_class='mb-3'),
            Field('password', css_class='mb-4'),
            Submit('submit', _('Se connecter'), css_class='btn btn-primary btn-lg w-100'),
        )


# ============================================================
# FORMULAIRE PROFIL
# ============================================================

class ProfilForm(forms.ModelForm):
    """Formulaire de modification du profil utilisateur."""

    class Meta:
        model = Utilisateur
        fields = ['first_name', 'last_name', 'email', 'telephone', 'service', 'photo']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_prenom'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_nom'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'id': 'id_email_profil'}),
            'telephone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+212 6XX-XXXXXX', 'id': 'id_telephone'}),
            'service': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_service'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_enctype = 'multipart/form-data'
        self.helper.layout = Layout(
            Row(
                Column('first_name', css_class='col-md-6'),
                Column('last_name', css_class='col-md-6'),
            ),
            Row(
                Column('email', css_class='col-md-6'),
                Column('telephone', css_class='col-md-6'),
            ),
            'service',
            'photo',
            Submit('submit', _('Mettre à jour le profil'), css_class='btn btn-success'),
        )


# ============================================================
# FORMULAIRE CHANGEMENT MOT DE PASSE
# ============================================================

class ChangerMotDePasseForm(PasswordChangeForm):
    """Formulaire de changement de mot de passe."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            'old_password',
            'new_password1',
            'new_password2',
            Submit('submit', _('Changer le mot de passe'), css_class='btn btn-warning'),
        )


# ============================================================
# FORMULAIRES GESTION UTILISATEURS
# ============================================================

class UtilisateurCreationForm(UserCreationForm):
    """Formulaire de création d'un nouvel utilisateur."""

    class Meta:
        model = Utilisateur
        fields = ['username', 'first_name', 'last_name', 'email', 'role', 'service', 'telephone', 'est_actif']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_username_create'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-select', 'id': 'id_role_select'}),
            'service': forms.TextInput(attrs={'class': 'form-control'}),
            'telephone': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not field.widget.attrs.get('class'):
                field.widget.attrs['class'] = 'form-control'
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(Column('username', css_class='col-md-6'), Column('role', css_class='col-md-6')),
            Row(Column('first_name', css_class='col-md-6'), Column('last_name', css_class='col-md-6')),
            Row(Column('email', css_class='col-md-6'), Column('telephone', css_class='col-md-6')),
            'service',
            Row(Column('password1', css_class='col-md-6'), Column('password2', css_class='col-md-6')),
            'est_actif',
            Submit('submit', _('Créer l\'utilisateur'), css_class='btn btn-primary'),
        )
    def save(self, commit=True):
        user = super().save(commit=False)
        # Gestion du rôle d'administration
        if user.role == Utilisateur.Role.ADMIN:
            user.is_staff = True
        else:
            user.is_staff = False
        
        # Synchronisation est_actif / is_active
        user.is_active = user.est_actif
        
        if commit:
            user.save()
        return user


class UtilisateurModificationForm(forms.ModelForm):
    """Formulaire de modification d'un utilisateur existant."""

    class Meta:
        model = Utilisateur
        fields = ['username', 'first_name', 'last_name', 'email', 'role', 'service', 'telephone', 'est_actif', 'is_staff']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_username_edit'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-select', 'id': 'id_role_edit'}),
            'service': forms.TextInput(attrs={'class': 'form-control'}),
            'telephone': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not field.widget.attrs.get('class'):
                field.widget.attrs['class'] = 'form-control'
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(Column('username', css_class='col-md-6'), Column('role', css_class='col-md-6')),
            Row(Column('first_name', css_class='col-md-6'), Column('last_name', css_class='col-md-6')),
            Row(Column('email', css_class='col-md-6'), Column('telephone', css_class='col-md-6')),
            'service',
            Row(Column('est_actif', css_class='col-md-6'), Column('is_staff', css_class='col-md-6')),
            Submit('submit', _('Enregistrer les modifications'), css_class='btn btn-success'),
        )

    def save(self, commit=True):
        user = super().save(commit=False)
        # Gestion automatique du staff si role ADMIN
        if user.role == Utilisateur.Role.ADMIN:
            user.is_staff = True
        
        # Synchronisation est_actif / is_active
        user.is_active = user.est_actif
        
        if commit:
            user.save()
        return user
