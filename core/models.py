"""
App Core - Modèles
Authentification personnalisée et modèles de base
MediCare Industries - StockPro
"""

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


# ============================================================
# MODÈLE UTILISATEUR PERSONNALISÉ
# ============================================================

class Utilisateur(AbstractUser):
    """
    Modèle Utilisateur étendu pour StockPro.
    Remplace le modèle User Django par défaut.
    """

    class Role(models.TextChoices):
        ADMIN = 'ADMIN', _('Administrateur')
        RESPONSABLE_STOCK = 'RESPONSABLE_STOCK', _('Responsable Stock')
        MAGASINIER = 'MAGASINIER', _('Magasinier')
        ACHETEUR = 'ACHETEUR', _('Acheteur')
        CONSULTANT = 'CONSULTANT', _('Consultant (Lecture seule)')

    # Champs supplémentaires
    role = models.CharField(
        max_length=30,
        choices=Role.choices,
        default=Role.MAGASINIER,
        verbose_name=_('Rôle'),
    )
    telephone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name=_('Téléphone'),
    )
    photo = models.ImageField(
        upload_to='utilisateurs/photos/',
        blank=True,
        null=True,
        verbose_name=_('Photo de profil'),
    )
    service = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_('Service / Département'),
    )
    date_derniere_connexion = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Dernière connexion'),
    )
    est_actif = models.BooleanField(
        default=True,
        verbose_name=_('Compte actif'),
    )

    class Meta:
        verbose_name = _('Utilisateur')
        verbose_name_plural = _('Utilisateurs')
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def est_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def peut_valider(self):
        return self.role in [self.Role.ADMIN, self.Role.RESPONSABLE_STOCK]

    @property
    def peut_saisir(self):
        return self.role in [
            self.Role.ADMIN,
            self.Role.RESPONSABLE_STOCK,
            self.Role.MAGASINIER,
            self.Role.ACHETEUR,
        ]


# ============================================================
# MODÈLE DE BASE ABSTRAIT
# ============================================================

class ModeleBase(models.Model):
    """
    Modèle abstrait avec champs d'audit communs.
    À hériter dans tous les modèles métier.
    """
    cree_par = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        verbose_name=_('Créé par'),
    )
    modifie_par = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        verbose_name=_('Modifié par'),
    )
    date_creation = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Date de création'),
    )
    date_modification = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Date de modification'),
    )
    est_actif = models.BooleanField(
        default=True,
        verbose_name=_('Actif'),
    )

    class Meta:
        abstract = True


# ============================================================
# JOURNAL D'ACTIVITÉ
# ============================================================

class JournalActivite(models.Model):
    """
    Enregistrement des actions utilisateurs (audit trail).
    """

    class TypeAction(models.TextChoices):
        CREATION = 'CREATE', _('Création')
        MODIFICATION = 'UPDATE', _('Modification')
        SUPPRESSION = 'DELETE', _('Suppression')
        CONNEXION = 'LOGIN', _('Connexion')
        DECONNEXION = 'LOGOUT', _('Déconnexion')
        EXPORT = 'EXPORT', _('Export')
        IMPRESSION = 'PRINT', _('Impression')

    utilisateur = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('Utilisateur'),
    )
    action = models.CharField(
        max_length=20,
        choices=TypeAction.choices,
        verbose_name=_('Action'),
    )
    modele = models.CharField(
        max_length=100,
        verbose_name=_('Modèle concerné'),
    )
    objet_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name=_('ID de l\'objet'),
    )
    description = models.TextField(
        verbose_name=_('Description'),
    )
    adresse_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name=_('Adresse IP'),
    )
    date_action = models.DateTimeField(
        default=timezone.now,
        verbose_name=_('Date et heure'),
    )
    donnees_avant = models.JSONField(
        null=True,
        blank=True,
        verbose_name=_('Données avant modification'),
    )
    donnees_apres = models.JSONField(
        null=True,
        blank=True,
        verbose_name=_('Données après modification'),
    )

    class Meta:
        verbose_name = _('Journal d\'activité')
        verbose_name_plural = _('Journal des activités')
        ordering = ['-date_action']

    def __str__(self):
        return f"{self.utilisateur} — {self.get_action_display()} — {self.date_action}"


# ============================================================
# PARAMÈTRES DE L'APPLICATION
# ============================================================

class ParametreApplication(models.Model):
    """
    Paramètres globaux configurables de StockPro.
    """
    cle = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_('Clé'),
    )
    valeur = models.TextField(
        verbose_name=_('Valeur'),
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Description'),
    )
    type_valeur = models.CharField(
        max_length=20,
        choices=[
            ('str', 'Texte'),
            ('int', 'Entier'),
            ('float', 'Décimal'),
            ('bool', 'Booléen'),
            ('json', 'JSON'),
        ],
        default='str',
        verbose_name=_('Type de valeur'),
    )
    modifie_le = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Dernière modification'),
    )

    class Meta:
        verbose_name = _('Paramètre')
        verbose_name_plural = _('Paramètres de l\'application')
        ordering = ['cle']

    def __str__(self):
        return f"{self.cle} = {self.valeur}"

    @classmethod
    def get(cls, cle, defaut=None):
        """Récupérer la valeur d'un paramètre."""
        try:
            return cls.objects.get(cle=cle).valeur
        except cls.DoesNotExist:
            return defaut


# ============================================================
# NOTIFICATION
# ============================================================

class Notification(models.Model):
    """
    Système de notifications internes pour les utilisateurs.
    """

    class TypeNotification(models.TextChoices):
        ALERTE_STOCK = 'STOCK', _('Alerte stock')
        PEREMPTION = 'PEREMPTION', _('Péremption proche')
        COMMANDE = 'COMMANDE', _('Commande en attente')
        SYSTEME = 'SYSTEME', _('Système')
        INFO = 'INFO', _('Information')

    class Priorite(models.TextChoices):
        HAUTE = 'HAUTE', _('Haute')
        NORMALE = 'NORMALE', _('Normale')
        BASSE = 'BASSE', _('Basse')

    destinataire = models.ForeignKey(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_('Destinataire'),
    )
    type_notification = models.CharField(
        max_length=20,
        choices=TypeNotification.choices,
        verbose_name=_('Type'),
    )
    titre = models.CharField(
        max_length=200,
        verbose_name=_('Titre'),
    )
    message = models.TextField(
        verbose_name=_('Message'),
    )
    priorite = models.CharField(
        max_length=10,
        choices=Priorite.choices,
        default=Priorite.NORMALE,
        verbose_name=_('Priorité'),
    )
    lue = models.BooleanField(
        default=False,
        verbose_name=_('Lue'),
    )
    date_envoi = models.DateTimeField(
        default=timezone.now,
        verbose_name=_('Date d\'envoi'),
    )
    date_lecture = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Date de lecture'),
    )
    lien = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name=_('Lien associé'),
    )

    class Meta:
        verbose_name = _('Notification')
        verbose_name_plural = _('Notifications')
        ordering = ['-date_envoi']

    def __str__(self):
        return f"{self.titre} → {self.destinataire}"

    def marquer_lue(self):
        if not self.lue:
            self.lue = True
            self.date_lecture = timezone.now()
            self.save(update_fields=['lue', 'date_lecture'])
