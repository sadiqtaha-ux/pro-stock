"""
App Magasin - Modèles
Plan 2D du magasin, Rayons, Allées, Emplacements
MediCare Industries - StockPro
"""

from django.db import models
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _

from core.models import ModeleBase


# ============================================================
# ZONE DE STOCKAGE
# ============================================================

class ZoneStockage(ModeleBase):
    """
    Zone principale du magasin (ex: Zone A, Zone Réfrigérée, Zone Matières Premières...).
    """

    class TypeZone(models.TextChoices):
        AMBIANT = 'AMBIANT', _('Température ambiante')
        REFRIGERE = 'REFRIGERE', _('Zone réfrigérée (2-8°C)')
        CONGELATION = 'CONGELATION', _('Zone de congélation')
        QUARANTAINE = 'QUARANTAINE', _('Zone de quarantaine')
        RECEPTION = 'RECEPTION', _('Zone de réception')
        EXPEDITION = 'EXPEDITION', _('Zone d\'expédition')
        PRODUITS_FINIS = 'PF', _('Produits finis')
        MATIERES_PREMIERES = 'MP', _('Matières premières')

    code = models.CharField(max_length=10, unique=True, verbose_name=_('Code zone'))
    libelle = models.CharField(max_length=100, verbose_name=_('Libellé'))
    type_zone = models.CharField(
        max_length=20, choices=TypeZone.choices,
        default=TypeZone.AMBIANT, verbose_name=_('Type de zone'),
    )
    description = models.TextField(blank=True, verbose_name=_('Description'))
    couleur = models.CharField(max_length=7, default='#e9ecef', verbose_name=_('Couleur (hex)'))

    # Position sur le plan 2D (coordonnées en pixels ou unités)
    position_x = models.FloatField(default=0, verbose_name=_('Position X'))
    position_y = models.FloatField(default=0, verbose_name=_('Position Y'))
    largeur = models.FloatField(default=100, verbose_name=_('Largeur'))
    hauteur = models.FloatField(default=100, verbose_name=_('Hauteur'))

    # Contraintes
    temperature_min = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    temperature_max = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    capacite_totale = models.FloatField(default=0, verbose_name=_('Capacité totale (m³)'))

    class Meta:
        verbose_name = _('Zone de stockage')
        verbose_name_plural = _('Zones de stockage')
        ordering = ['code']

    def __str__(self):
        return f"{self.code} — {self.libelle}"


# ============================================================
# RAYON
# ============================================================

class Rayon(ModeleBase):
    """
    Rayon au sein d'une zone (ex: Rayon A1, Rayon Réfrigéré 1...).
    """
    zone = models.ForeignKey(
        ZoneStockage,
        on_delete=models.CASCADE,
        related_name='rayons',
        verbose_name=_('Zone'),
    )
    code = models.CharField(max_length=10, verbose_name=_('Code rayon'))
    libelle = models.CharField(max_length=100, verbose_name=_('Libellé'))
    orientation = models.CharField(
        max_length=10,
        choices=[('H', _('Horizontal')), ('V', _('Vertical'))],
        default='V',
        verbose_name=_('Orientation'),
    )
    nombre_niveaux = models.PositiveSmallIntegerField(default=5, verbose_name=_('Nombre de niveaux'))
    nombre_colonnes = models.PositiveSmallIntegerField(default=10, verbose_name=_('Nombre de colonnes'))

    # Position sur le plan 2D
    position_x = models.FloatField(default=0)
    position_y = models.FloatField(default=0)
    largeur = models.FloatField(default=50)
    hauteur = models.FloatField(default=20)

    class Meta:
        verbose_name = _('Rayon')
        verbose_name_plural = _('Rayons')
        unique_together = ['zone', 'code']
        ordering = ['zone', 'code']

    def __str__(self):
        return f"{self.zone.code}-{self.code}"


# ============================================================
# EMPLACEMENT
# ============================================================

class Emplacement(ModeleBase):
    """
    Emplacement physique précis dans le magasin.
    Identifié par : Zone-Rayon-Niveau-Colonne ex: A-R1-N2-C05
    """

    class StatutEmplacement(models.TextChoices):
        LIBRE = 'LIBRE', _('Libre')
        OCCUPE = 'OCCUPE', _('Occupé')
        RESERVE = 'RESERVE', _('Réservé')
        BLOQUE = 'BLOQUE', _('Bloqué (maintenance)')
        QUARANTAINE = 'QUARANTAINE', _('Quarantaine')

    rayon = models.ForeignKey(
        Rayon,
        on_delete=models.CASCADE,
        related_name='emplacements',
        verbose_name=_('Rayon'),
    )
    code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name=_('Code emplacement'),
        help_text=_('Ex: A-R1-N2-C05'),
    )
    niveau = models.PositiveSmallIntegerField(
        verbose_name=_('Niveau'),
        help_text=_('1 = niveau bas, 5 = niveau haut'),
    )
    colonne = models.PositiveSmallIntegerField(verbose_name=_('Colonne'))
    statut = models.CharField(
        max_length=20,
        choices=StatutEmplacement.choices,
        default=StatutEmplacement.LIBRE,
        verbose_name=_('Statut'),
    )

    # Capacité
    capacite_poids_max = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_('Capacité poids max (kg)'),
    )
    capacite_volume_max = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
        verbose_name=_('Capacité volume max (m³)'),
    )

    # Conditions de stockage autorisées
    type_produit_autorise = models.CharField(
        max_length=20,
        choices=[
            ('TOUS', _('Tous types')),
            ('AMBIANT', _('Température ambiante')),
            ('REFRIGERE', _('Réfrigéré')),
            ('DANGEREUX', _('Produits dangereux')),
        ],
        default='TOUS',
        verbose_name=_('Type de produit autorisé'),
    )

    notes = models.CharField(max_length=200, blank=True, verbose_name=_('Notes'))

    class Meta:
        verbose_name = _('Emplacement')
        verbose_name_plural = _('Emplacements')
        ordering = ['rayon', 'niveau', 'colonne']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['statut']),
        ]

    def __str__(self):
        return f"{self.code} ({self.get_statut_display()})"

    def save(self, *args, **kwargs):
        """Auto-génération du code emplacement."""
        if not self.code:
            self.code = f"{self.rayon}-N{self.niveau:02d}-C{self.colonne:02d}"
        super().save(*args, **kwargs)

    @property
    def est_libre(self):
        return self.statut == self.StatutEmplacement.LIBRE

    @property
    def produit_stocke(self):
        """Produit actuellement stocké à cet emplacement."""
        return self.produits.filter(statut='ACTIF').first()


# ============================================================
# PLAN DU MAGASIN (Métadonnées de configuration)
# ============================================================

class PlanMagasin(ModeleBase):
    """
    Configuration du plan 2D du magasin.
    Dimensions et paramètres d'affichage.
    """
    nom = models.CharField(max_length=100, default='Plan principal', verbose_name=_('Nom du plan'))
    largeur_totale = models.FloatField(default=1000, verbose_name=_('Largeur totale (pixels)'))
    hauteur_totale = models.FloatField(default=600, verbose_name=_('Hauteur totale (pixels)'))
    echelle = models.FloatField(default=1.0, verbose_name=_('Échelle (pixels/mètre)'))
    image_fond = models.ImageField(
        upload_to='magasin/plans/',
        null=True,
        blank=True,
        verbose_name=_('Image de fond du plan'),
    )
    est_actif = models.BooleanField(default=True)
    config_affichage = models.JSONField(
        default=dict,
        verbose_name=_('Configuration d\'affichage JSON'),
        help_text=_('Paramètres de couleurs, légendes, etc.'),
    )

    class Meta:
        verbose_name = _('Plan du magasin')
        verbose_name_plural = _('Plans du magasin')

    def __str__(self):
        return f"Plan : {self.nom}"
