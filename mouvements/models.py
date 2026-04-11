"""
App Mouvements - Modèles
Entrées, sorties, transferts et historique des mouvements de stock
MediCare Industries - StockPro
"""

from django.db import models
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.conf import settings

from core.models import ModeleBase


# ============================================================
# MOUVEMENT DE STOCK
# ============================================================

class MouvementStock(ModeleBase):
    """
    Enregistrement de chaque mouvement de stock :
    entrée, sortie, ajustement, transfert.
    Modèle central de la traçabilité des stocks.
    """

    class TypeMouvement(models.TextChoices):
        ENTREE = 'ENTREE', _('Entrée en stock')
        SORTIE = 'SORTIE', _('Sortie de stock')
        AJUSTEMENT_POS = 'AJUST_POS', _('Ajustement positif (inventaire)')
        AJUSTEMENT_NEG = 'AJUST_NEG', _('Ajustement négatif (inventaire)')
        TRANSFERT = 'TRANSFERT', _('Transfert inter-emplacements')
        RETOUR = 'RETOUR', _('Retour fournisseur')
        PERTE = 'PERTE', _('Perte / Destruction')
        PEREMPTION = 'PEREMPTION', _('Mise au rebut (péremption)')

    class StatutMouvement(models.TextChoices):
        BROUILLON = 'BROUILLON', _('Brouillon')
        EN_ATTENTE = 'EN_ATTENTE', _('En attente de validation')
        VALIDE = 'VALIDE', _('Validé')
        ANNULE = 'ANNULE', _('Annulé')

    # Numéro unique
    numero = models.CharField(
        max_length=20,
        unique=True,
        verbose_name=_('N° de mouvement'),
    )

    # Type et statut
    type_mouvement = models.CharField(
        max_length=20,
        choices=TypeMouvement.choices,
        verbose_name=_('Type de mouvement'),
    )
    statut = models.CharField(
        max_length=20,
        choices=StatutMouvement.choices,
        default=StatutMouvement.BROUILLON,
        verbose_name=_('Statut'),
    )

    # Produit et lot
    produit = models.ForeignKey(
        'produits.Produit',
        on_delete=models.PROTECT,
        related_name='mouvements',
        verbose_name=_('Produit'),
    )
    lot = models.ForeignKey(
        'produits.LotProduit',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mouvements',
        verbose_name=_('Lot'),
    )

    # Quantités
    quantite = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        validators=[MinValueValidator(0.001)],
        verbose_name=_('Quantité'),
    )
    unite = models.ForeignKey(
        'produits.UniteMesure',
        on_delete=models.PROTECT,
        verbose_name=_('Unité'),
    )
    prix_unitaire = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=0,
        verbose_name=_('Prix unitaire (DH)'),
    )

    # Stock avant/après (snapshot)
    stock_avant = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0,
        verbose_name=_('Stock avant mouvement'),
    )
    stock_apres = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0,
        verbose_name=_('Stock après mouvement'),
    )

    # Dates
    date_mouvement = models.DateTimeField(
        default=timezone.now,
        verbose_name=_('Date du mouvement'),
    )
    date_validation = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Date de validation'),
    )

    # Références
    reference_document = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Référence document'),
        help_text=_('N° BL, N° BC, N° facture, etc.'),
    )
    bon_livraison = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('N° Bon de livraison'),
    )
    fournisseur = models.ForeignKey(
        'produits.Fournisseur',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('Fournisseur'),
    )
    commande = models.ForeignKey(
        'approvisionnement.CommandeAchat',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mouvements',
        verbose_name=_('Commande associée'),
    )

    # Emplacement source/destination
    emplacement_source = models.ForeignKey(
        'magasin.Emplacement',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mouvements_sortie',
        verbose_name=_('Emplacement source'),
    )
    emplacement_destination = models.ForeignKey(
        'magasin.Emplacement',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mouvements_entree',
        verbose_name=_('Emplacement destination'),
    )

    # Validation
    valide_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mouvements_valides',
        verbose_name=_('Validé par'),
    )
    motif = models.TextField(
        blank=True,
        verbose_name=_('Motif / Observation'),
    )

    class Meta:
        verbose_name = _('Mouvement de stock')
        verbose_name_plural = _('Mouvements de stock')
        ordering = ['-date_mouvement']
        indexes = [
            models.Index(fields=['numero']),
            models.Index(fields=['produit', 'date_mouvement']),
            models.Index(fields=['type_mouvement', 'statut']),
            models.Index(fields=['date_mouvement']),
        ]

    def __str__(self):
        return f"{self.numero} — {self.get_type_mouvement_display()} — {self.produit.code}"

    @property
    def montant_total(self):
        return self.quantite * self.prix_unitaire

    @property
    def est_entree(self):
        return self.type_mouvement in [
            self.TypeMouvement.ENTREE,
            self.TypeMouvement.AJUSTEMENT_POS,
            self.TypeMouvement.RETOUR,
        ]

    @property
    def est_sortie(self):
        return self.type_mouvement in [
            self.TypeMouvement.SORTIE,
            self.TypeMouvement.AJUSTEMENT_NEG,
            self.TypeMouvement.PERTE,
            self.TypeMouvement.PEREMPTION,
        ]

    def save(self, *args, **kwargs):
        """Auto-génération du numéro de mouvement."""
        if not self.numero:
            prefixes = {
                'ENTREE': 'ENT',
                'SORTIE': 'SOR',
                'AJUST_POS': 'AJP',
                'AJUST_NEG': 'AJN',
                'TRANSFERT': 'TRF',
                'RETOUR': 'RET',
                'PERTE': 'PTE',
                'PEREMPTION': 'PER',
            }
            prefix = prefixes.get(self.type_mouvement, 'MVT')
            annee = timezone.now().strftime('%Y%m')
            count = MouvementStock.objects.filter(
                numero__startswith=prefix
            ).count() + 1
            self.numero = f"{prefix}-{annee}-{count:05d}"
        super().save(*args, **kwargs)


# ============================================================
# BON D'ENTRÉE
# ============================================================

class BonEntree(ModeleBase):
    """
    Bon de réception des marchandises fournisseurs.
    Regroupe plusieurs lignes de mouvement d'entrée.
    """

    class Statut(models.TextChoices):
        BROUILLON = 'BROUILLON', _('Brouillon')
        RECEPTION_PARTIELLE = 'PARTIELLE', _('Réception partielle')
        RECEPTION_TOTALE = 'TOTALE', _('Réception totale')
        VALIDE = 'VALIDE', _('Validé')
        ANNULE = 'ANNULE', _('Annulé')

    numero = models.CharField(max_length=20, unique=True, verbose_name=_('N° bon d\'entrée'))
    fournisseur = models.ForeignKey(
        'produits.Fournisseur',
        on_delete=models.PROTECT,
        related_name='bons_entree',
        verbose_name=_('Fournisseur'),
    )
    commande = models.ForeignKey(
        'approvisionnement.CommandeAchat',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bons_entree',
        verbose_name=_('Bon de commande associé'),
    )
    date_reception = models.DateField(default=timezone.now, verbose_name=_('Date de réception'))
    reference_fournisseur = models.CharField(max_length=100, blank=True, verbose_name=_('Réf. fournisseur'))
    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.BROUILLON)
    valide_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='bons_entree_valides',
        verbose_name=_('Validé par'),
    )
    date_validation = models.DateTimeField(null=True, blank=True, verbose_name=_('Date validation'))
    notes = models.TextField(blank=True, verbose_name=_('Notes'))

    class Meta:
        verbose_name = _('Bon d\'entrée')
        verbose_name_plural = _('Bons d\'entrée')
        ordering = ['-date_reception']

    def __str__(self):
        return f"{self.numero} — {self.fournisseur.raison_sociale}"

    def save(self, *args, **kwargs):
        if not self.numero:
            annee = timezone.now().strftime('%Y%m')
            count = BonEntree.objects.count() + 1
            self.numero = f"BE-{annee}-{count:05d}"
        super().save(*args, **kwargs)


# ============================================================
# BON DE SORTIE
# ============================================================

class BonSortie(ModeleBase):
    """
    Bon de sortie pour les demandes internes.
    """

    class Statut(models.TextChoices):
        BROUILLON = 'BROUILLON', _('Brouillon')
        EN_ATTENTE = 'EN_ATTENTE', _('En attente de validation')
        VALIDE = 'VALIDE', _('Validé')
        PREPARE = 'PREPARE', _('Préparé')
        EXPEDIE = 'EXPEDIE', _('Expédié / Livré')
        ANNULE = 'ANNULE', _('Annulé')

    numero = models.CharField(max_length=20, unique=True, verbose_name=_('N° bon de sortie'))
    demandeur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='bons_sortie_demandes',
        verbose_name=_('Demandeur'),
    )
    service_demandeur = models.CharField(max_length=100, blank=True, verbose_name=_('Service demandeur'))
    date_demande = models.DateField(default=timezone.now, verbose_name=_('Date de demande'))
    date_livraison_souhaitee = models.DateField(null=True, blank=True, verbose_name=_('Date de livraison souhaitée'))
    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.BROUILLON)
    motif = models.CharField(max_length=200, blank=True, verbose_name=_('Motif de sortie'))
    valide_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='bons_sortie_valides',
        verbose_name=_('Validé par'),
    )
    date_validation = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = _('Bon de sortie')
        verbose_name_plural = _('Bons de sortie')
        ordering = ['-date_demande']

    def __str__(self):
        return f"{self.numero} — {self.service_demandeur}"

    def save(self, *args, **kwargs):
        if not self.numero:
            annee = timezone.now().strftime('%Y%m')
            count = BonSortie.objects.count() + 1
            self.numero = f"BS-{annee}-{count:05d}"
        super().save(*args, **kwargs)


# ============================================================
# INVENTAIRE
# ============================================================

class Inventaire(ModeleBase):
    """
    Inventaire physique du stock.
    """

    class Statut(models.TextChoices):
        EN_COURS = 'EN_COURS', _('En cours')
        TERMINE = 'TERMINE', _('Terminé')
        VALIDE = 'VALIDE', _('Validé')
        ANNULE = 'ANNULE', _('Annulé')

    numero = models.CharField(max_length=20, unique=True, verbose_name=_('N° inventaire'))
    date_debut = models.DateField(verbose_name=_('Date de début'))
    date_fin = models.DateField(null=True, blank=True, verbose_name=_('Date de fin'))
    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.EN_COURS)
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='inventaires',
        verbose_name=_('Responsable'),
    )
    type_inventaire = models.CharField(
        max_length=20,
        choices=[
            ('COMPLET', _('Inventaire complet')),
            ('PARTIEL', _('Inventaire partiel')),
            ('TOURNANT', _('Inventaire tournant')),
        ],
        default='COMPLET',
        verbose_name=_('Type d\'inventaire'),
    )
    observations = models.TextField(blank=True, verbose_name=_('Observations'))

    class Meta:
        verbose_name = _('Inventaire')
        verbose_name_plural = _('Inventaires')
        ordering = ['-date_debut']

    def __str__(self):
        return f"{self.numero} — {self.get_type_inventaire_display()} — {self.date_debut}"

    def save(self, *args, **kwargs):
        if not self.numero:
            annee = timezone.now().strftime('%Y')
            count = Inventaire.objects.filter(date_debut__year=timezone.now().year).count() + 1
            self.numero = f"INV-{annee}-{count:03d}"
        super().save(*args, **kwargs)


class LigneInventaire(models.Model):
    """Ligne d'inventaire physique pour un produit."""
    inventaire = models.ForeignKey(
        Inventaire,
        on_delete=models.CASCADE,
        related_name='lignes',
        verbose_name=_('Inventaire'),
    )
    produit = models.ForeignKey(
        'produits.Produit',
        on_delete=models.CASCADE,
        related_name='lignes_inventaire',
        verbose_name=_('Produit'),
    )
    lot = models.ForeignKey(
        'produits.LotProduit',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('Lot'),
    )
    quantite_theorique = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        verbose_name=_('Quantité théorique (système)'),
    )
    quantite_comptee = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
        verbose_name=_('Quantité comptée'),
    )
    ecart = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0,
        verbose_name=_('Écart'),
    )
    observations = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name = _('Ligne d\'inventaire')
        verbose_name_plural = _('Lignes d\'inventaire')
        unique_together = ['inventaire', 'produit', 'lot']

    def __str__(self):
        return f"{self.inventaire.numero} / {self.produit.code}"

    def calculer_ecart(self):
        if self.quantite_comptee is not None:
            self.ecart = self.quantite_comptee - self.quantite_theorique
        return self.ecart
