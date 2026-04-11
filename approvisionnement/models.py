"""
approvisionnement/models.py
MediCare Industries — Modèles : BonCommande, PlanMRP
"""

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


# ============================================================
# BON DE COMMANDE
# ============================================================

class BonCommande(models.Model):
    """Bon de commande fournisseur généré manuellement ou par une méthode d'appro."""

    class MethodeDeclenchement(models.TextChoices):
        REAPPRO_FIXE   = "REAPPRO_FIXE",   _("Réappro fixe")
        POINT_COMMANDE = "POINT_COMMANDE", _("Point de commande")
        RECOMPLETEMENT = "RECOMPLETEMENT", _("Récompletement")
        MRP            = "MRP",            _("MRP")
        MANUEL         = "MANUEL",         _("Manuel")

    class Statut(models.TextChoices):
        BROUILLON  = "BROUILLON",  _("Brouillon")
        ENVOYE     = "ENVOYE",     _("Envoyé")
        CONFIRME   = "CONFIRME",   _("Confirmé")
        RECU       = "RECU",       _("Reçu")
        ANNULE     = "ANNULE",     _("Annulé")

    # --- Référence auto-générée : BC-YYYY-XXXX ---
    reference = models.CharField(
        _("Référence"), max_length=20, unique=True, blank=True,
        help_text=_("Générée automatiquement : BC-YYYY-XXXX")
    )

    # --- Relations ---
    matiere = models.ForeignKey(
        "produits.MatierePremiere",
        on_delete=models.PROTECT,
        related_name="bons_commande",
        verbose_name=_("Matière première"),
    )
    fournisseur = models.ForeignKey(
        "produits.Fournisseur",
        on_delete=models.PROTECT,
        related_name="bons_commande",
        verbose_name=_("Fournisseur"),
    )

    # --- Quantités & prix ---
    quantite_commandee = models.DecimalField(
        _("Quantité commandée"), max_digits=14, decimal_places=4,
        validators=[MinValueValidator(0)]
    )
    prix_unitaire = models.DecimalField(
        _("Prix unitaire (DH)"), max_digits=12, decimal_places=4,
        validators=[MinValueValidator(0)], default=0
    )
    montant_total = models.DecimalField(
        _("Montant total (DH)"), max_digits=14, decimal_places=2,
        validators=[MinValueValidator(0)], default=0,
        editable=False
    )

    # --- Méthode & statut ---
    methode_declenchement = models.CharField(
        _("Méthode de déclenchement"), max_length=20,
        choices=MethodeDeclenchement.choices,
        default=MethodeDeclenchement.MANUEL
    )
    statut = models.CharField(
        _("Statut"), max_length=15,
        choices=Statut.choices, default=Statut.BROUILLON
    )

    # --- Dates ---
    date_creation          = models.DateTimeField(_("Date de création"), auto_now_add=True)
    date_envoi             = models.DateTimeField(_("Date d'envoi"), null=True, blank=True)
    date_reception_prevue  = models.DateField(_("Réception prévue"), null=True, blank=True)
    date_reception_reelle  = models.DateField(_("Réception réelle"), null=True, blank=True)

    # --- Utilisateur & notes ---
    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True,
        related_name="bons_commande_crees",
        verbose_name=_("Créé par"),
    )
    notes = models.TextField(_("Notes"), blank=True)

    class Meta:
        verbose_name        = _("Bon de commande")
        verbose_name_plural = _("Bons de commande")
        ordering            = ["-date_creation"]
        indexes = [
            models.Index(fields=["statut"]),
            models.Index(fields=["reference"]),
        ]

    def __str__(self):
        return f"{self.reference} — {self.matiere}"

    # --- Génération automatique de la référence ---
    def save(self, *args, **kwargs):
        if not self.reference:
            annee = timezone.now().year
            dernier = (
                BonCommande.objects
                .filter(reference__startswith=f"BC-{annee}-")
                .order_by("-reference")
                .first()
            )
            if dernier:
                try:
                    seq = int(dernier.reference.split("-")[-1]) + 1
                except (ValueError, IndexError):
                    seq = 1
            else:
                seq = 1
            self.reference = f"BC-{annee}-{seq:04d}"

        # Calcul automatique du montant total
        self.montant_total = self.quantite_commandee * self.prix_unitaire
        super().save(*args, **kwargs)


# ============================================================
# PLAN MRP
# ============================================================

class PlanMRP(models.Model):
    """Ligne de planification MRP sur une période donnée."""

    class Statut(models.TextChoices):
        CALCULE  = "CALCULE",  _("Calculé")
        CONFIRME = "CONFIRME", _("Confirmé")
        LANCE    = "LANCE",    _("Lancé")

    matiere = models.ForeignKey(
        "produits.MatierePremiere",
        on_delete=models.CASCADE,
        related_name="plans_mrp",
        verbose_name=_("Matière première"),
    )

    # --- Période ---
    periode = models.DateField(
        _("Période (début de semaine / mois)"),
        help_text=_("Date de début de la période de planification")
    )

    # --- Calculs MRP ---
    besoin_brut        = models.DecimalField(
        _("Besoin brut"), max_digits=14, decimal_places=4,
        validators=[MinValueValidator(0)], default=0
    )
    stock_debut_periode = models.DecimalField(
        _("Stock en début de période"), max_digits=14, decimal_places=4,
        validators=[MinValueValidator(0)], default=0
    )
    besoin_net         = models.DecimalField(
        _("Besoin net"), max_digits=14, decimal_places=4,
        validators=[MinValueValidator(0)], default=0,
        help_text=_("max(0, Besoin brut − Stock début − Réceptions prévues)")
    )
    quantite_proposee  = models.DecimalField(
        _("Quantité d'ordre proposée"), max_digits=14, decimal_places=4,
        validators=[MinValueValidator(0)], default=0
    )
    stock_fin_periode  = models.DecimalField(
        _("Stock en fin de période"), max_digits=14, decimal_places=4,
        default=0
    )

    # --- Statut ---
    statut = models.CharField(
        _("Statut"), max_length=10,
        choices=Statut.choices, default=Statut.CALCULE
    )

    class Meta:
        verbose_name        = _("Plan MRP")
        verbose_name_plural = _("Plans MRP")
        ordering            = ["matiere", "periode"]
        unique_together     = [("matiere", "periode")]
        indexes = [
            models.Index(fields=["matiere", "periode"]),
            models.Index(fields=["statut"]),
        ]

    def __str__(self):
        return f"MRP — {self.matiere} — {self.periode:%Y-%m}"
