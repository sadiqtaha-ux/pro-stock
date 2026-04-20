"""
approvisionnement/models.py
MediCare Industries — Modèles : BonCommande, PlanMRP, PropositionCommande
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


# ============================================================
# PROPOSITION DE COMMANDE (Planificateur)
# ============================================================

class PropositionCommande(models.Model):
    """
    Proposition de commande générée automatiquement par le planificateur.
    L'acheteur la valide, modifie ou rejette avant qu'elle devienne un BonCommande.
    La méthode est héritée directement depuis matiere.methode_approvisionnement.
    """

    class Statut(models.TextChoices):
        PROPOSEE  = "PROPOSEE",  _("Proposée")
        VALIDEE   = "VALIDEE",   _("Validée")
        REJETEE   = "REJETEE",   _("Rejetée")
        CONVERTIE = "CONVERTIE", _("Convertie en BC")

    matiere = models.ForeignKey(
        "produits.MatierePremiere",
        on_delete=models.CASCADE,
        related_name="propositions",
        verbose_name=_("Matière première"),
    )
    methode = models.CharField(
        _("Méthode (héritée)"), max_length=20,
        help_text=_("Copie de matiere.methode_approvisionnement au moment du calcul")
    )
    quantite_proposee = models.DecimalField(
        _("Quantité proposée"), max_digits=14, decimal_places=4,
        validators=[MinValueValidator(0)]
    )
    quantite_validee = models.DecimalField(
        _("Quantité validée"), max_digits=14, decimal_places=4,
        validators=[MinValueValidator(0)], null=True, blank=True,
        help_text=_("Modifiable par l'acheteur avant conversion en BC")
    )
    detail_calcul = models.JSONField(
        _("Détail du calcul"), default=dict,
        help_text=_("Stocke les paramètres utilisés: stock, ROP, QEC, période...")
    )
    urgence = models.BooleanField(
        _("Urgente"), default=False,
        help_text=_("True si stock en rupture ou sous stock de sécurité")
    )
    date_generation = models.DateTimeField(_("Date de génération"), auto_now_add=True)
    date_besoin = models.DateField(
        _("Date de besoin"), null=True, blank=True,
        help_text=_("Date limite avant rupture estimée")
    )
    statut = models.CharField(
        _("Statut"), max_length=15,
        choices=Statut.choices, default=Statut.PROPOSEE
    )
    bon_commande = models.OneToOneField(
        BonCommande, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="proposition_origine",
        verbose_name=_("Bon de commande généré"),
    )
    note_acheteur = models.TextField(_("Note acheteur"), blank=True)

    class Meta:
        verbose_name        = _("Proposition de commande")
        verbose_name_plural = _("Propositions de commande")
        ordering            = ["-urgence", "date_besoin"]
        indexes = [
            models.Index(fields=["statut"]),
            models.Index(fields=["matiere", "statut"]),
        ]

    def __str__(self):
        return f"Prop. {self.methode} — {self.matiere} — {self.quantite_proposee}"

    @property
    def quantite_finale(self):
        """Quantité à commander : validée si modifiée, sinon proposée."""
        return self.quantite_validee if self.quantite_validee is not None \
               else self.quantite_proposee
