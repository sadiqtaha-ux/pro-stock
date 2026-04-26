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
        SECHE = 'SECHE', _('Zone sèche')
        FROIDE = 'FROIDE', _('Zone froide (2-8°C)')
        TEMPEREE = 'TEMPEREE', _('Température ambiante (15-25°C)')
        QUARANTAINE = 'QUARANTAINE', _('Zone de quarantaine')
        RECEPTION = 'RECEPTION', _('Zone de réception')
        EXPEDITION = 'EXPEDITION', _('Zone d\'expédition')
        MATIERES_PREMIERES = 'MATIERES_PREMIERES', _('Matières premières')
        PRODUITS_FINIS = 'PRODUITS_FINIS', _('Produits finis')
        MIXTE = 'MIXTE', _('Zone mixte')

    code = models.CharField(max_length=10, unique=True, verbose_name=_('Code zone'))
    nom = models.CharField(max_length=100, verbose_name=_('Nom de la zone'), blank=True)
    libelle = models.CharField(max_length=100, verbose_name=_('Libellé / Description courte'))
    type_zone = models.CharField(
        max_length=20, choices=TypeZone.choices,
        default=TypeZone.SECHE, verbose_name=_('Type de zone'),
    )
    description = models.TextField(blank=True, verbose_name=_('Description détaillée'))
    couleur = models.CharField(max_length=7, default='#e9ecef', verbose_name=_('Couleur (hex)'))

    # Position sur le plan 2D
    position_x = models.FloatField(default=0, verbose_name=_('Position X'))
    position_y = models.FloatField(default=0, verbose_name=_('Position Y'))
    largeur = models.FloatField(default=100, verbose_name=_('Largeur'))
    hauteur = models.FloatField(default=100, verbose_name=_('Hauteur'))

    # Contraintes & Environnement
    temperature_min = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    temperature_max = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    humidite_min = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    humidite_max = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    
    capacite_totale = models.FloatField(default=0, verbose_name=_('Capacité totale (m³)'))
    ordre = models.PositiveIntegerField(default=0, verbose_name=_('Ordre d\'affichage'))
    actif = models.BooleanField(default=True, verbose_name=_('Actif'))

    class Meta:
        verbose_name = _('Zone de stockage')
        verbose_name_plural = _('Zones de stockage')
        ordering = ['ordre', 'code']

    def __str__(self):
        return f"{self.code} — {self.nom or self.libelle}"


# ============================================================
# RAYON
# ============================================================

class Rayon(ModeleBase):
    """
    Rayon au sein d'une zone (ex: Rayon A1, Rayon Réfrigéré 1...).
    """
    class TypeStock(models.TextChoices):
        MATIERE_PREMIERE = 'MATIERE_PREMIERE', _('Matières Premières')
        PRODUIT_FINI = 'PRODUIT_FINI', _('Produits Finis')
        MIXTE = 'MIXTE', _('Mixte')

    class StatutRayon(models.TextChoices):
        ACTIF = 'ACTIF', _('Actif')
        SATURE = 'SATURE', _('Saturé')
        BLOQUE = 'BLOQUE', _('Bloqué')
        MAINTENANCE = 'MAINTENANCE', _('En maintenance')

    zone = models.ForeignKey(
        ZoneStockage,
        on_delete=models.CASCADE,
        related_name='rayons',
        verbose_name=_('Zone'),
    )
    code = models.CharField(max_length=10, verbose_name=_('Code rayon'))
    nom = models.CharField(max_length=100, verbose_name=_('Nom du rayon'), blank=True)
    libelle = models.CharField(max_length=100, verbose_name=_('Libellé'))
    
    type_stock = models.CharField(
        max_length=20, choices=TypeStock.choices,
        default=TypeStock.MIXTE, verbose_name=_('Type de stock')
    )
    
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
    
    couleur = models.CharField(max_length=7, default='#ffffff', verbose_name=_('Couleur'))
    capacite_max = models.FloatField(default=0, verbose_name=_('Capacité max'))
    statut = models.CharField(
        max_length=20, choices=StatutRayon.choices,
        default=StatutRayon.ACTIF, verbose_name=_('Statut')
    )
    actif = models.BooleanField(default=True, verbose_name=_('Actif'))

    class Meta:
        verbose_name = _('Rayon')
        verbose_name_plural = _('Rayons')
        unique_together = ['zone', 'code']
        ordering = ['zone', 'code']

    def __str__(self):
        return f"{self.zone.code}-{self.code}"


# ============================================================
# NIVEAU DE RAYON
# ============================================================

class NiveauRayon(ModeleBase):
    """
    Niveau horizontal au sein d'un rayon.
    """
    rayon = models.ForeignKey(
        Rayon, on_delete=models.CASCADE, 
        related_name='niveaux', verbose_name=_('Rayon')
    )
    numero = models.PositiveSmallIntegerField(verbose_name=_('Numéro du niveau'))
    libelle = models.CharField(max_length=50, blank=True, verbose_name=_('Libellé'))
    capacite_max = models.FloatField(default=0, verbose_name=_('Capacité maximale'))
    actif = models.BooleanField(default=True, verbose_name=_('Actif'))

    class Meta:
        verbose_name = _('Niveau de rayon')
        verbose_name_plural = _('Niveaux de rayons')
        ordering = ['rayon', 'numero']
        unique_together = ['rayon', 'numero']

    def __str__(self):
        return f"{self.rayon} - Niveau {self.numero}"


# ============================================================
# AFFECTATION DE STOCK
# ============================================================

class AffectationStock(ModeleBase):
    """
    Lien entre un niveau de rayon et un article (MP ou PF).
    """
    niveau = models.ForeignKey(
        NiveauRayon, on_delete=models.CASCADE,
        related_name='affectations', verbose_name=_('Niveau de rayon')
    )
    matiere_premiere = models.ForeignKey(
        'produits.MatierePremiere', on_delete=models.CASCADE,
        null=True, blank=True, related_name='affectations_magasin',
        verbose_name=_('Matière Première')
    )
    produit_fini = models.ForeignKey(
        'produits.ProduitFini', on_delete=models.CASCADE,
        null=True, blank=True, related_name='affectations_magasin',
        verbose_name=_('Produit Fini')
    )
    
    quantite_affectee = models.DecimalField(
        max_digits=14, decimal_places=4, default=0,
        verbose_name=_('Quantité affectée')
    )
    capacite_reservee = models.FloatField(
        default=0, verbose_name=_('Capacité réservée')
    )
    date_affectation = models.DateTimeField(auto_now_add=True, verbose_name=_('Date d\'affectation'))
    actif = models.BooleanField(default=True, verbose_name=_('Actif'))

    class Meta:
        verbose_name = _('Affectation de stock')
        verbose_name_plural = _('Affectations de stock')

    def __str__(self):
        article = self.matiere_premiere or self.produit_fini
        return f"{article} @ {self.niveau}"

    def clean(self):
        from django.core.exceptions import ValidationError
        
        # 1. Validation : MP ou PF, pas les deux, au moins un
        if self.matiere_premiere and self.produit_fini:
            raise ValidationError(_("Une affectation ne peut pas concerner à la fois une matière première et un produit fini."))
        if not self.matiere_premiere and not self.produit_fini:
            raise ValidationError(_("L'affectation doit concerner soit une matière première, soit un produit fini."))

        # 2. Validation : Compatibilité du type de stock du rayon
        rayon = self.niveau.rayon
        if self.matiere_premiere and rayon.type_stock == Rayon.TypeStock.PRODUIT_FINI:
            raise ValidationError(_("Ce rayon est réservé aux produits finis."))
        if self.produit_fini and rayon.type_stock == Rayon.TypeStock.MATIERE_PREMIERE:
            raise ValidationError(_("Ce rayon est réservé aux matières premières."))

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


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
        BLOQUE      = 'BLOQUE',      _('Bloqué (maintenance)')
        QUARANTAINE = 'QUARANTAINE', _('Quarantaine')
        SATURE      = 'SATURE',      _('Saturé')

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


# ============================================================
# DÉLIMITATION DU PLAN
# ============================================================

class DelimitationPlan(ModeleBase):
    """
    Tracé visuel sur le plan (couloir, séparation, périmètre...).
    Indépendant du stockage.
    """
    class TypeDelimitation(models.TextChoices):
        COULOIR = 'COULOIR', _('Couloir')
        SEPARATION = 'SEPARATION', _('Séparation physique')
        PERIMETRE = 'PERIMETRE', _('Périmètre fonctionnel')
        SECURITE = 'SECURITE', _('Zone de sécurité')
        AUTRE = 'AUTRE', _('Autre')

    class StyleTrait(models.TextChoices):
        PLEIN = 'PLEIN', _('Trait plein')
        POINTILLE = 'POINTILLE', _('Trait pointillé')

    nom = models.CharField(max_length=100, verbose_name=_('Nom de la délimitation'))
    type_delimitation = models.CharField(
        max_length=20, choices=TypeDelimitation.choices,
        default=TypeDelimitation.AUTRE, verbose_name=_('Type')
    )
    
    position_x = models.FloatField(default=0)
    position_y = models.FloatField(default=0)
    largeur = models.FloatField(default=100)
    hauteur = models.FloatField(default=100)
    
    couleur = models.CharField(max_length=7, default='#000000', verbose_name=_('Couleur'))
    epaisseur = models.PositiveSmallIntegerField(default=2, verbose_name=_('Épaisseur (px)'))
    style_trait = models.CharField(
        max_length=10, choices=StyleTrait.choices,
        default=StyleTrait.PLEIN, verbose_name=_('Style de trait')
    )
    actif = models.BooleanField(default=True)

    class Meta:
        verbose_name = _('Délimitation de plan')
        verbose_name_plural = _('Délimitations de plan')

    def __str__(self):
        return self.nom
