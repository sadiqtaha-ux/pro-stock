"""
produits/models.py
MediCare Industries — Modèles : Fournisseur, UnitesMesure, MatierePremiere
"""

from django.db import models
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _


# ============================================================
# FOURNISSEUR
# ============================================================

class Fournisseur(models.Model):
    """Fournisseur de matières premières."""

    nom          = models.CharField(_("Nom / Raison sociale"), max_length=200)
    contact      = models.CharField(_("Personne de contact"), max_length=150, blank=True)
    email        = models.EmailField(_("Email"), blank=True)
    telephone    = models.CharField(_("Téléphone"), max_length=30, blank=True)
    adresse      = models.TextField(_("Adresse"), blank=True)
    ville        = models.CharField(_("Ville"), max_length=100, blank=True)
    pays         = models.CharField(_("Pays"), max_length=100, default="Maroc")
    actif        = models.BooleanField(_("Actif"), default=True)
    date_creation = models.DateTimeField(_("Date de création"), auto_now_add=True)

    class Meta:
        verbose_name        = _("Fournisseur")
        verbose_name_plural = _("Fournisseurs")
        ordering            = ["nom"]

    def __str__(self):
        return self.nom


# ============================================================
# UNITÉ DE MESURE
# ============================================================

class UnitesMesure(models.Model):
    """Unité de mesure (kg, L, unités, boîtes…)."""

    nom     = models.CharField(_("Nom"), max_length=50, unique=True)
    symbole = models.CharField(_("Symbole"), max_length=10)

    class Meta:
        verbose_name        = _("Unité de mesure")
        verbose_name_plural = _("Unités de mesure")
        ordering            = ["nom"]

    def __str__(self):
        return f"{self.nom} ({self.symbole})"


# ============================================================
# MATIÈRE PREMIÈRE
# ============================================================

class MatierePremiere(models.Model):
    """Matière première pharmaceutique gérée en stock."""

    # --- Énumérations ---
    class Categorie(models.TextChoices):
        PRINCIPE_ACTIF   = "PRINCIPE_ACTIF",   _("Principe actif")
        EXCIPIENT        = "EXCIPIENT",         _("Excipient")
        CONDITIONNEMENT  = "CONDITIONNEMENT",   _("Conditionnement")

    class MethodeApprovisionnement(models.TextChoices):
        REAPPRO_FIXE   = "REAPPRO_FIXE",   _("Réappro fixe (Q, T)")
        POINT_COMMANDE = "POINT_COMMANDE", _("Point de commande (ROP)")
        RECOMPLETEMENT = "RECOMPLETEMENT", _("Récompletement (S, T)")
        MRP            = "MRP",            _("MRP")

    class ZoneStockage(models.TextChoices):
        FROIDE   = "FROIDE",   _("Zone froide (2 – 8 °C)")
        TEMPEREE = "TEMPEREE", _("Température ambiante (15 – 25 °C)")
        SECHE    = "SECHE",    _("Zone sèche")

    # --- Identification ---
    reference   = models.CharField(
        _("Référence"), max_length=30, unique=True,
        help_text=_("Ex : API-001, EXC-042")
    )
    nom         = models.CharField(_("Nom"), max_length=200)
    description = models.TextField(_("Description"), blank=True)

    # --- Classification ---
    categorie = models.CharField(
        _("Catégorie"), max_length=20,
        choices=Categorie.choices, default=Categorie.PRINCIPE_ACTIF
    )

    # --- Relations ---
    unite               = models.ForeignKey(
        UnitesMesure, on_delete=models.PROTECT,
        related_name="matieres", verbose_name=_("Unité de mesure")
    )
    fournisseur_principal = models.ForeignKey(
        Fournisseur, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="matieres_principales",
        verbose_name=_("Fournisseur principal")
    )

    # --- Financier ---
    prix_unitaire = models.DecimalField(
        _("Prix unitaire (DH)"), max_digits=12, decimal_places=4,
        validators=[MinValueValidator(0)], default=0
    )

    # --- Stock ---
    stock_actuel   = models.DecimalField(
        _("Stock actuel"), max_digits=14, decimal_places=4,
        validators=[MinValueValidator(0)], default=0
    )
    stock_minimum  = models.DecimalField(
        _("Stock minimum"), max_digits=14, decimal_places=4,
        validators=[MinValueValidator(0)], default=0
    )
    stock_maximum  = models.DecimalField(
        _("Stock maximum"), max_digits=14, decimal_places=4,
        validators=[MinValueValidator(0)], default=0
    )
    stock_securite = models.DecimalField(
        _("Stock de sécurité"), max_digits=14, decimal_places=4,
        validators=[MinValueValidator(0)], default=0
    )

    # --- Paramètres d'approvisionnement ---
    methode_approvisionnement = models.CharField(
        _("Méthode d'approvisionnement"), max_length=20,
        choices=MethodeApprovisionnement.choices,
        default=MethodeApprovisionnement.POINT_COMMANDE
    )
    point_commande       = models.DecimalField(
        _("Point de commande (ROP)"), max_digits=14, decimal_places=4,
        validators=[MinValueValidator(0)], default=0,
        help_text=_("Seuil déclencheur d'une commande (méthode ROP)")
    )
    qec                  = models.DecimalField(
        _("QEC — Quantité économique de commande"), max_digits=14, decimal_places=4,
        validators=[MinValueValidator(0)], default=0,
        help_text=_("Calculée par la formule de Wilson : √(2·D·K / (h·Pu))")
    )
    delai_livraison_jours = models.PositiveSmallIntegerField(
        _("Délai de livraison (jours)"), default=7
    )
    periode_reappro_jours = models.PositiveSmallIntegerField(
        _("Période de réappro (jours)"), default=30,
        help_text=_("Utilisé pour les méthodes Réappro Fixe et Récompletement")
    )
    taux_rebut            = models.DecimalField(
        _("Taux de rebut (MRP)"), max_digits=5, decimal_places=4,
        validators=[MinValueValidator(0)], default=0,
        help_text=_("Proportion de perte en production (ex : 0.02 = 2 %)")
    )

    # --- Stockage physique ---
    zone_stockage = models.CharField(
        _("Zone de stockage"), max_length=10,
        choices=ZoneStockage.choices, default=ZoneStockage.TEMPEREE
    )
    emplacement   = models.CharField(
        _("Emplacement"), max_length=20, blank=True,
        help_text=_("Ex : A1, B3, C12")
    )

    # --- Métadonnées ---
    actif            = models.BooleanField(_("Actif"), default=True)
    date_creation    = models.DateTimeField(_("Date de création"), auto_now_add=True)
    date_modification = models.DateTimeField(_("Dernière modification"), auto_now=True)

    class Meta:
        verbose_name        = _("Matière première")
        verbose_name_plural = _("Matières premières")
        ordering            = ["reference"]
        indexes = [
            models.Index(fields=["reference"]),
            models.Index(fields=["categorie"]),
            models.Index(fields=["methode_approvisionnement"]),
        ]

    def __str__(self):
        return f"[{self.reference}] {self.nom}"

    # --- Properties ---
    @property
    def taux_remplissage(self) -> float:
        """
        Taux de remplissage du stock en % par rapport au stock maximum.
        Retourne 0 si stock_maximum = 0 (évite la division par zéro).
        """
        if not self.stock_maximum:
            return 0.0
        return round(float(self.stock_actuel) / float(self.stock_maximum) * 100, 1)

    @property
    def est_en_rupture(self) -> bool:
        return self.stock_actuel <= 0

    @property
    def est_en_alerte(self) -> bool:
        return 0 < self.stock_actuel <= self.stock_minimum

    @property
    def valeur_stock(self):
        """Valeur du stock actuel en DH."""
        return self.stock_actuel * self.prix_unitaire
