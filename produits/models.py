"""
App Produits - Modèles
Matières premières, Fournisseurs, Catégories, Unités de mesure
MediCare Industries - StockPro
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.conf import settings

from core.models import ModeleBase


# ============================================================
# UNITÉ DE MESURE
# ============================================================

class UniteMesure(models.Model):
    """
    Unités de mesure utilisées pour les produits.
    Ex: kg, g, L, mL, comprimé, flacon, etc.
    """
    code = models.CharField(
        max_length=10,
        unique=True,
        verbose_name=_('Code'),
        help_text=_('Ex: kg, g, L, mL, cp, fl'),
    )
    libelle = models.CharField(
        max_length=50,
        verbose_name=_('Libellé'),
    )
    libelle_pluriel = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('Libellé pluriel'),
    )
    categorie = models.CharField(
        max_length=30,
        choices=[
            ('MASSE', _('Masse')),
            ('VOLUME', _('Volume')),
            ('QUANTITE', _('Quantité')),
            ('LONGUEUR', _('Longueur')),
            ('AUTRE', _('Autre')),
        ],
        default='QUANTITE',
        verbose_name=_('Catégorie'),
    )
    est_actif = models.BooleanField(default=True, verbose_name=_('Actif'))

    class Meta:
        verbose_name = _('Unité de mesure')
        verbose_name_plural = _('Unités de mesure')
        ordering = ['libelle']

    def __str__(self):
        return f"{self.libelle} ({self.code})"


# ============================================================
# CATÉGORIE DE PRODUIT
# ============================================================

class CategorieProduit(ModeleBase):
    """
    Catégories hiérarchiques pour classifier les produits.
    """
    code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name=_('Code'),
    )
    libelle = models.CharField(
        max_length=100,
        verbose_name=_('Libellé'),
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Description'),
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sous_categories',
        verbose_name=_('Catégorie parente'),
    )
    couleur = models.CharField(
        max_length=7,
        default='#0d6efd',
        verbose_name=_('Couleur (hex)'),
    )
    icone = models.CharField(
        max_length=50,
        blank=True,
        default='bi-box',
        verbose_name=_('Icône Bootstrap'),
    )

    class Meta:
        verbose_name = _('Catégorie de produit')
        verbose_name_plural = _('Catégories de produits')
        ordering = ['libelle']

    def __str__(self):
        if self.parent:
            return f"{self.parent.libelle} > {self.libelle}"
        return self.libelle


# ============================================================
# FOURNISSEUR
# ============================================================

class Fournisseur(ModeleBase):
    """
    Fournisseurs de matières premières.
    """

    class Statut(models.TextChoices):
        ACTIF = 'ACTIF', _('Actif')
        INACTIF = 'INACTIF', _('Inactif')
        SUSPENDU = 'SUSPENDU', _('Suspendu')
        PROSPECT = 'PROSPECT', _('Prospect')

    code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name=_('Code fournisseur'),
    )
    raison_sociale = models.CharField(
        max_length=200,
        verbose_name=_('Raison sociale'),
    )
    nom_commercial = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('Nom commercial'),
    )
    statut = models.CharField(
        max_length=20,
        choices=Statut.choices,
        default=Statut.ACTIF,
        verbose_name=_('Statut'),
    )

    # Coordonnées
    adresse = models.TextField(verbose_name=_('Adresse'))
    ville = models.CharField(max_length=100, verbose_name=_('Ville'))
    code_postal = models.CharField(max_length=10, blank=True, verbose_name=_('Code postal'))
    pays = models.CharField(max_length=50, default='Maroc', verbose_name=_('Pays'))
    telephone = models.CharField(max_length=20, blank=True, verbose_name=_('Téléphone'))
    fax = models.CharField(max_length=20, blank=True, verbose_name=_('Fax'))
    email = models.EmailField(blank=True, verbose_name=_('Email'))
    site_web = models.URLField(blank=True, verbose_name=_('Site web'))

    # Contact principal
    contact_nom = models.CharField(max_length=100, blank=True, verbose_name=_('Nom du contact'))
    contact_telephone = models.CharField(max_length=20, blank=True, verbose_name=_('Téléphone contact'))
    contact_email = models.EmailField(blank=True, verbose_name=_('Email contact'))
    contact_poste = models.CharField(max_length=100, blank=True, verbose_name=_('Poste contact'))

    # Informations commerciales
    ice = models.CharField(max_length=15, blank=True, verbose_name=_('ICE'))
    if_numero = models.CharField(max_length=20, blank=True, verbose_name=_('N° IF'))
    rc = models.CharField(max_length=20, blank=True, verbose_name=_('RC'))
    delai_livraison_moyen = models.PositiveIntegerField(
        default=7,
        verbose_name=_('Délai de livraison moyen (jours)'),
    )
    conditions_paiement = models.CharField(
        max_length=100,
        default='30 jours net',
        verbose_name=_('Conditions de paiement'),
    )
    remise_habituelle = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name=_('Remise habituelle (%)'),
    )
    note_evaluation = models.PositiveSmallIntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name=_('Évaluation (1-5)'),
    )
    notes = models.TextField(blank=True, verbose_name=_('Notes internes'))

    class Meta:
        verbose_name = _('Fournisseur')
        verbose_name_plural = _('Fournisseurs')
        ordering = ['raison_sociale']

    def __str__(self):
        return f"[{self.code}] {self.raison_sociale}"

    @property
    def est_actif(self):
        return self.statut == self.Statut.ACTIF


# ============================================================
# PRODUIT (MATIÈRE PREMIÈRE)
# ============================================================

class Produit(ModeleBase):
    """
    Matière première / Produit géré en stock.
    Modèle central de l'application StockPro.
    """

    class Statut(models.TextChoices):
        ACTIF = 'ACTIF', _('Actif')
        INACTIF = 'INACTIF', _('Inactif')
        ARCHIVE = 'ARCHIVE', _('Archivé')
        DISCONTINUE = 'DISCONTINUE', _('Discontinué')

    class TypeStockage(models.TextChoices):
        AMBIANT = 'AMBIANT', _('Température ambiante')
        REFRIGERE = 'REFRIGERE', _('Réfrigéré (2-8°C)')
        CONGELE = 'CONGELE', _('Congelé (< -18°C)')
        CONTROLE = 'CONTROLE', _('Température contrôlée')

    class ClasseABC(models.TextChoices):
        A = 'A', _('Classe A (priorité haute)')
        B = 'B', _('Classe B (priorité moyenne)')
        C = 'C', _('Classe C (priorité basse)')

    # Identification
    code = models.CharField(
        max_length=30,
        unique=True,
        verbose_name=_('Code produit'),
    )
    code_barre = models.CharField(
        max_length=50,
        blank=True,
        unique=True,
        null=True,
        verbose_name=_('Code barre'),
    )
    designation = models.CharField(
        max_length=200,
        verbose_name=_('Désignation'),
    )
    designation_arabe = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('Désignation en arabe'),
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Description'),
    )
    photo = models.ImageField(
        upload_to='produits/photos/',
        blank=True,
        null=True,
        verbose_name=_('Photo'),
    )
    statut = models.CharField(
        max_length=20,
        choices=Statut.choices,
        default=Statut.ACTIF,
        verbose_name=_('Statut'),
    )

    # Classification
    categorie = models.ForeignKey(
        CategorieProduit,
        on_delete=models.PROTECT,
        related_name='produits',
        verbose_name=_('Catégorie'),
    )
    classe_abc = models.CharField(
        max_length=1,
        choices=ClasseABC.choices,
        default=ClasseABC.B,
        verbose_name=_('Classe ABC'),
    )
    fournisseur_principal = models.ForeignKey(
        Fournisseur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='produits_principaux',
        verbose_name=_('Fournisseur principal'),
    )

    # Unités
    unite_stock = models.ForeignKey(
        UniteMesure,
        on_delete=models.PROTECT,
        related_name='produits_stock',
        verbose_name=_('Unité de stockage'),
    )
    unite_achat = models.ForeignKey(
        UniteMesure,
        on_delete=models.PROTECT,
        related_name='produits_achat',
        null=True,
        blank=True,
        verbose_name=_('Unité d\'achat'),
    )
    coefficient_conversion = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=1,
        verbose_name=_('Coefficient de conversion'),
        help_text=_('Nombre d\'unités de stock par unité d\'achat'),
    )

    # Paramètres de stock
    stock_actuel = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0,
        verbose_name=_('Stock actuel'),
    )
    stock_minimum = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0,
        verbose_name=_('Stock minimum (seuil d\'alerte)'),
    )
    stock_maximum = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0,
        verbose_name=_('Stock maximum'),
    )
    stock_securite = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0,
        verbose_name=_('Stock de sécurité'),
    )
    point_commande = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0,
        verbose_name=_('Point de commande'),
    )
    quantite_economique = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0,
        verbose_name=_('Quantité économique de commande (QEC)'),
    )

    # Prix
    prix_unitaire_achat = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name=_('Prix unitaire d\'achat (DH)'),
    )
    prix_unitaire_revient = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name=_('Prix de revient unitaire (DH)'),
    )
    tva = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=20,
        verbose_name=_('TVA (%)'),
    )

    # Stockage physique
    type_stockage = models.CharField(
        max_length=20,
        choices=TypeStockage.choices,
        default=TypeStockage.AMBIANT,
        verbose_name=_('Conditions de stockage'),
    )
    temperature_min = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        verbose_name=_('Température min (°C)'),
    )
    temperature_max = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        verbose_name=_('Température max (°C)'),
    )
    duree_conservation = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_('Durée de conservation (mois)'),
    )

    # Méthode d'approvisionnement
    methode_appro = models.CharField(
        max_length=30,
        choices=[
            ('REAPPRO_FIXE', _('Réaprovisionnement à quantité fixe')),
            ('POINT_COMMANDE', _('Point de commande (ROP)')),
            ('RECOMPLETEMENT', _('Récompletement périodique')),
            ('MRP', _('MRP — Calcul des besoins')),
        ],
        default='POINT_COMMANDE',
        verbose_name=_('Méthode d\'approvisionnement'),
    )
    delai_reappro = models.PositiveIntegerField(
        default=7,
        verbose_name=_('Délai de réapprovisionnement (jours)'),
    )
    periodicite_reappro = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_('Périodicité de réapprovisionnement (jours)'),
    )

    # Emplacement magasin
    emplacement = models.ForeignKey(
        'magasin.Emplacement',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='produits',
        verbose_name=_('Emplacement'),
    )

    class Meta:
        verbose_name = _('Produit')
        verbose_name_plural = _('Produits')
        ordering = ['designation']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['designation']),
            models.Index(fields=['statut']),
            models.Index(fields=['categorie']),
        ]

    def __str__(self):
        return f"[{self.code}] {self.designation}"

    @property
    def valeur_stock(self):
        """Valeur totale du stock (quantité × prix unitaire)."""
        return self.stock_actuel * self.prix_unitaire_revient

    @property
    def est_en_rupture(self):
        return self.stock_actuel <= 0

    @property
    def est_en_alerte(self):
        return 0 < self.stock_actuel <= self.stock_minimum

    @property
    def est_surstock(self):
        return self.stock_maximum > 0 and self.stock_actuel > self.stock_maximum

    @property
    def taux_couverture(self):
        """Taux de remplissage du stock (%)."""
        if self.stock_maximum > 0:
            return min(100, float(self.stock_actuel / self.stock_maximum * 100))
        return 0

    @property
    def statut_stock(self):
        """Statut visuel du stock."""
        if self.est_en_rupture:
            return 'rupture'
        elif self.est_en_alerte:
            return 'alerte'
        elif self.est_surstock:
            return 'surstock'
        return 'normal'


# ============================================================
# LOT DE PRODUIT
# ============================================================

class LotProduit(ModeleBase):
    """
    Lot de produit avec numéro de lot et date de péremption.
    Permet la traçabilité FIFO/FEFO.
    """

    class Statut(models.TextChoices):
        DISPONIBLE = 'DISPONIBLE', _('Disponible')
        QUARANTAINE = 'QUARANTAINE', _('Quarantaine')
        LIBERE = 'LIBERE', _('Libéré')
        REJETE = 'REJETE', _('Rejeté')
        EPUISE = 'EPUISE', _('Épuisé')

    produit = models.ForeignKey(
        Produit,
        on_delete=models.CASCADE,
        related_name='lots',
        verbose_name=_('Produit'),
    )
    numero_lot = models.CharField(
        max_length=50,
        verbose_name=_('Numéro de lot'),
    )
    date_fabrication = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Date de fabrication'),
    )
    date_peremption = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Date de péremption'),
    )
    quantite_initiale = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        verbose_name=_('Quantité initiale'),
    )
    quantite_restante = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        verbose_name=_('Quantité restante'),
    )
    statut = models.CharField(
        max_length=20,
        choices=Statut.choices,
        default=Statut.DISPONIBLE,
        verbose_name=_('Statut'),
    )
    origine = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('Origine / Fournisseur'),
    )
    certificat_analyse = models.FileField(
        upload_to='lots/certificats/',
        null=True,
        blank=True,
        verbose_name=_('Certificat d\'analyse'),
    )
    notes = models.TextField(blank=True, verbose_name=_('Notes'))

    class Meta:
        verbose_name = _('Lot de produit')
        verbose_name_plural = _('Lots de produits')
        ordering = ['date_peremption', 'date_fabrication']
        unique_together = ['produit', 'numero_lot']

    def __str__(self):
        return f"{self.produit.code} / Lot {self.numero_lot}"

    @property
    def jours_avant_peremption(self):
        if self.date_peremption:
            delta = self.date_peremption - timezone.now().date()
            return delta.days
        return None

    @property
    def est_proche_peremption(self):
        jours = self.jours_avant_peremption
        if jours is not None:
            return 0 <= jours <= 90
        return False

    @property
    def est_perime(self):
        jours = self.jours_avant_peremption
        if jours is not None:
            return jours < 0
        return False


# ============================================================
# TARIF FOURNISSEUR
# ============================================================

class TarifFournisseur(ModeleBase):
    """
    Tarification fournisseur par produit avec historique.
    """
    produit = models.ForeignKey(
        Produit,
        on_delete=models.CASCADE,
        related_name='tarifs',
        verbose_name=_('Produit'),
    )
    fournisseur = models.ForeignKey(
        Fournisseur,
        on_delete=models.CASCADE,
        related_name='tarifs',
        verbose_name=_('Fournisseur'),
    )
    reference_fournisseur = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('Référence fournisseur'),
    )
    prix_unitaire = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        verbose_name=_('Prix unitaire (DH)'),
    )
    quantite_minimum = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=1,
        verbose_name=_('Quantité minimale de commande'),
    )
    remise = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name=_('Remise (%)'),
    )
    date_validite_debut = models.DateField(
        verbose_name=_('Valable à partir du'),
    )
    date_validite_fin = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Valable jusqu\'au'),
    )
    est_principal = models.BooleanField(
        default=False,
        verbose_name=_('Tarif principal'),
    )
    notes = models.TextField(blank=True, verbose_name=_('Notes'))

    class Meta:
        verbose_name = _('Tarif fournisseur')
        verbose_name_plural = _('Tarifs fournisseurs')
        ordering = ['-date_validite_debut']

    def __str__(self):
        return f"{self.produit.code} / {self.fournisseur.raison_sociale} — {self.prix_unitaire} DH"

    @property
    def prix_net(self):
        return self.prix_unitaire * (1 - self.remise / 100)
