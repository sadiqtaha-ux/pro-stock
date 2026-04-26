"""
produits/models.py
MediCare Industries — Modèles : Fournisseur, UnitesMesure, MatierePremiere, ProduitFini, Nomenclature
"""

from django.db import models
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _


# ============================================================
# FOURNISSEUR
# ============================================================

class Fournisseur(models.Model):
    """Fournisseur de matières premières."""

    class Statut(models.TextChoices):
        ACTIF        = "ACTIF",        _("Actif")
        A_SURVEILLER = "A_SURVEILLER", _("À surveiller")
        INACTIF      = "INACTIF",      _("Inactif")
        BLOQUE       = "BLOQUE",       _("Bloqué")

    nom          = models.CharField(_("Nom / Raison sociale"), max_length=200)
    contact      = models.CharField(_("Personne de contact"), max_length=150, blank=True)
    email        = models.EmailField(_("Email"), blank=True)
    telephone    = models.CharField(_("Téléphone"), max_length=30, blank=True)
    adresse      = models.TextField(_("Adresse"), blank=True)
    ville        = models.CharField(_("Ville"), max_length=100, blank=True)
    pays         = models.CharField(_("Pays"), max_length=100, default="Maroc")
    statut       = models.CharField(
        _("Statut"), max_length=20, choices=Statut.choices, default=Statut.ACTIF
    )
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
    autorise_decimales = models.BooleanField(
        _("Autorise les décimales"), default=True,
        help_text=_("Décocher pour les unités discrètes (Boîte, Pièce, etc.) qui ne gèrent que des entiers.")
    )

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

    class ClasseABC(models.TextChoices):
        A = "A", _("Classe A — Articles critiques (forte valeur)")
        B = "B", _("Classe B — Articles intermédiaires")
        C = "C", _("Classe C — Articles à faible valeur")

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
    lot_minimum = models.DecimalField(
        _("Lot minimum"), max_digits=14, decimal_places=4,
        validators=[MinValueValidator(0)], default=1,
        help_text=_("Quantité minimale à commander si un besoin est détecté")
    )
    multiple_lot = models.DecimalField(
        _("Multiple de lot"), max_digits=14, decimal_places=4,
        validators=[MinValueValidator(1)], default=1,
        help_text=_("La commande doit être un multiple de cette quantité")
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

    # --- Classification ABC ---
    classe_abc = models.CharField(
        _("Classe ABC"), max_length=1,
        choices=ClasseABC.choices, blank=True, default="",
        help_text=_(
            "Calculée automatiquement par la commande 'calculer_abc'. "
            "A = forte valeur (0–80 %), B = intermédiaire (80–95 %), C = faible valeur (95–100 %)."
        )
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
        return self.stock_actuel * self.prix_unitaire

    @property
    def valeur_consommation_annuelle(self):
        """
        Calcule la valeur totale des sorties sur les 12 derniers mois.
        Retourne (somme des quantités SORTIE) * prix_unitaire.
        """
        from django.utils import timezone
        import datetime
        from django.db.models import Sum

        un_an_ago = timezone.now() - datetime.timedelta(days=365)

        # On récupère la somme des quantités pour les mouvements de type SORTIE
        # Note: on utilise related_name="mouvements" défini dans MouvementStock
        somme = self.mouvements.filter(
            type_mouvement="SORTIE",
            date_mouvement__gte=un_an_ago
        ).aggregate(total=Sum('quantite'))['total'] or 0

        return float(somme) * float(self.prix_unitaire)


# ============================================================
# PRODUIT FINI
# ============================================================

class ProduitFini(models.Model):
    """Produit fini fabriqué à partir de matières premières."""

    class Categorie(models.TextChoices):
        MEDICAMENT  = "MEDICAMENT",  _("Médicament")
        DISPOSITIF  = "DISPOSITIF",  _("Dispositif médical")
        CONSOMMABLE = "CONSOMMABLE", _("Consommable")
        AUTRE       = "AUTRE",       _("Autre")

    class Statut(models.TextChoices):
        EN_PRODUCTION = "EN_PRODUCTION", _("En production")
        DISPONIBLE    = "DISPONIBLE",    _("Disponible")
        PERIME        = "PERIME",        _("Périmé")
        RAPPEL        = "RAPPEL",        _("Rappel produit")
        QUARANTAINE   = "QUARANTAINE",   _("Quarantaine")

    class ZoneStockage(models.TextChoices):
        FROIDE   = "FROIDE",   _("Zone froide (2 – 8 °C)")
        TEMPEREE = "TEMPEREE", _("Température ambiante (15 – 25 °C)")
        SECHE    = "SECHE",    _("Zone sèche")

    reference   = models.CharField(
        _("Référence"), max_length=30, unique=True,
        help_text=_("Ex : PF-001, MED-042")
    )
    nom         = models.CharField(_("Nom"), max_length=200)
    description = models.TextField(_("Description"), blank=True)
    categorie   = models.CharField(
        _("Catégorie"), max_length=20,
        choices=Categorie.choices, default=Categorie.MEDICAMENT
    )
    statut = models.CharField(
        _("Statut"), max_length=20,
        choices=Statut.choices, default=Statut.DISPONIBLE
    )

    unite = models.ForeignKey(
        UnitesMesure, on_delete=models.PROTECT,
        related_name="produits_finis", verbose_name=_("Unité de mesure")
    )

    stock_actuel  = models.DecimalField(
        _("Stock actuel"), max_digits=14, decimal_places=4,
        validators=[MinValueValidator(0)], default=0
    )
    stock_minimum = models.DecimalField(
        _("Stock minimum"), max_digits=14, decimal_places=4,
        validators=[MinValueValidator(0)], default=0
    )
    stock_maximum = models.DecimalField(
        _("Stock maximum"), max_digits=14, decimal_places=4,
        validators=[MinValueValidator(0)], default=0
    )
    prix_unitaire = models.DecimalField(
        _("Prix unitaire (DH)"), max_digits=12, decimal_places=4,
        validators=[MinValueValidator(0)], default=0
    )

    zone_stockage = models.CharField(
        _("Zone de stockage"), max_length=10,
        choices=ZoneStockage.choices, default=ZoneStockage.TEMPEREE
    )
    emplacement = models.CharField(
        _("Emplacement"), max_length=20, blank=True,
        help_text=_("Ex : A1, PF-B3")
    )

    numero_lot      = models.CharField(_("Numéro de lot"), max_length=50, blank=True)
    date_peremption = models.DateField(_("Date de péremption"), null=True, blank=True)

    actif             = models.BooleanField(_("Actif"), default=True)
    date_creation     = models.DateTimeField(_("Date de création"), auto_now_add=True)
    date_modification = models.DateTimeField(_("Dernière modification"), auto_now=True)

    class Meta:
        verbose_name        = _("Produit fini")
        verbose_name_plural = _("Produits finis")
        ordering            = ["reference"]
        indexes = [
            models.Index(fields=["reference"]),
            models.Index(fields=["statut"]),
            models.Index(fields=["categorie"]),
        ]

    def __str__(self):
        return f"[{self.reference}] {self.nom}"

    @property
    def est_en_rupture(self) -> bool:
        return self.stock_actuel <= 0

    @property
    def est_en_alerte(self) -> bool:
        return 0 < self.stock_actuel <= self.stock_minimum

    @property
    def valeur_stock(self):
        return self.stock_actuel * self.prix_unitaire

    @property
    def valeur_consommation_annuelle(self):
        """Identique à MatierePremiere pour le calcul ABC / Valeur."""
        from django.utils import timezone
        import datetime
        from django.db.models import Sum

        un_an_ago = timezone.now() - datetime.timedelta(days=365)

        somme = self.mouvements.filter(
            type_mouvement="SORTIE",
            date_mouvement__gte=un_an_ago
        ).aggregate(total=Sum('quantite'))['total'] or 0

        return float(somme) * float(self.prix_unitaire)


# ============================================================
# NOMENCLATURE
# ============================================================

class Nomenclature(models.Model):
    """En-tête de nomenclature pour un produit fini."""

    produit_fini = models.ForeignKey(
        ProduitFini, on_delete=models.CASCADE,
        related_name="nomenclatures", verbose_name=_("Produit fini")
    )
    nom = models.CharField(_("Nom"), max_length=100, blank=True)
    version = models.CharField(_("Version"), max_length=20, default="V1")
    actif = models.BooleanField(_("Active"), default=True)
    date_creation = models.DateTimeField(_("Date de création"), auto_now_add=True)
    date_modification = models.DateTimeField(_("Dernière modification"), auto_now=True)

    class Meta:
        verbose_name = _("Nomenclature")
        verbose_name_plural = _("Nomenclatures")
        ordering = ["-actif", "produit_fini", "-date_creation"]

    def __str__(self):
        return f"Nomenclature {self.version} - {self.produit_fini.nom}"


class LigneNomenclature(models.Model):
    """Lien entre nomenclature et ses composants (matières premières)."""

    nomenclature = models.ForeignKey(
        Nomenclature, on_delete=models.CASCADE,
        related_name="lignes", verbose_name=_("Nomenclature")
    )
    matiere = models.ForeignKey(
        MatierePremiere, on_delete=models.CASCADE,
        related_name="utilise_dans", verbose_name=_("Matière première / Composant")
    )
    quantite_par_unite = models.DecimalField(
        _("Quantité par unité"), max_digits=14, decimal_places=6,
        validators=[MinValueValidator(0.000001)],
        help_text=_("Quantité de matière nécessaire pour fabriquer 1 unité de produit fini")
    )
    taux_perte = models.DecimalField(
        _("Taux de perte spécifique (%)"), max_digits=5, decimal_places=4,
        validators=[MinValueValidator(0)], default=0,
        help_text=_("Perte additionnelle pour ce produit spécifique (ex: 0.05 pour 5%)")
    )
    obligatoire = models.BooleanField(_("Obligatoire"), default=True)
    ordre_affichage = models.PositiveSmallIntegerField(_("Ordre"), default=10)

    class Meta:
        verbose_name        = _("Ligne de nomenclature")
        verbose_name_plural = _("Lignes de nomenclature")
        ordering            = ["nomenclature", "ordre_affichage"]
        unique_together     = ["nomenclature", "matiere"]

    def __str__(self):
        return f"{self.matiere.nom} pour {self.nomenclature.produit_fini.nom}"
