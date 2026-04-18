"""
mouvements/models.py
MediCare Industries — Modèle : MouvementStock
"""

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _


class MouvementStock(models.Model):
    """
    Traçabilité complète de chaque mouvement de stock
    (entrée ou sortie) sur une matière première.
    """

    class TypeMouvement(models.TextChoices):
        ENTREE = "ENTREE", _("Entrée")
        SORTIE = "SORTIE", _("Sortie")

    # --- Matière concernée ---
    matiere = models.ForeignKey(
        "produits.MatierePremiere",
        on_delete=models.PROTECT,
        related_name="mouvements",
        verbose_name=_("Matière première"),
    )

    # --- Type & quantités ---
    type_mouvement  = models.CharField(
        _("Type de mouvement"), max_length=10,
        choices=TypeMouvement.choices
    )
    quantite        = models.DecimalField(
        _("Quantité mouvementée"), max_digits=14, decimal_places=4,
        validators=[MinValueValidator(0)]
    )
    quantite_avant  = models.DecimalField(
        _("Stock avant mouvement"), max_digits=14, decimal_places=4,
        validators=[MinValueValidator(0)], default=0,
        help_text=_("Snapshot du stock juste avant ce mouvement")
    )
    quantite_apres  = models.DecimalField(
        _("Stock après mouvement"), max_digits=14, decimal_places=4,
        default=0,
        help_text=_("Calculé automatiquement lors de la validation")
    )

    # --- Date & traçabilité ---
    date_mouvement  = models.DateTimeField(_("Date du mouvement"), auto_now_add=True)
    motif           = models.CharField(_("Motif"), max_length=255, blank=True)
    numero_lot      = models.CharField(_("Numéro de lot"), max_length=50, blank=True)
    date_peremption = models.DateField(_("Date de péremption du lot"), null=True, blank=True)

    # --- Utilisateur & lien commande ---
    operateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True,
        related_name="mouvements_effectues",
        verbose_name=_("Opérateur"),
    )
    bon_commande = models.ForeignKey(
        "approvisionnement.BonCommande",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="mouvements",
        verbose_name=_("Bon de commande associé"),
    )

    class Meta:
        verbose_name        = _("Mouvement de stock")
        verbose_name_plural = _("Mouvements de stock")
        ordering            = ["-date_mouvement"]
        indexes = [
            models.Index(fields=["matiere", "date_mouvement"]),
            models.Index(fields=["type_mouvement"]),
            models.Index(fields=["numero_lot"]),
        ]

    def __str__(self):
        signe = "+" if self.type_mouvement == self.TypeMouvement.ENTREE else "-"
        return f"{self.date_mouvement:%d/%m/%Y %H:%M} | {self.matiere} | {signe}{self.quantite}"

    # --- Calcul automatique de quantite_apres avant sauvegarde ---
    def save(self, *args, **kwargs):
        if self.type_mouvement == self.TypeMouvement.ENTREE:
            self.quantite_apres = self.quantite_avant + self.quantite
        else:
            self.quantite_apres = self.quantite_avant - self.quantite
        super().save(*args, **kwargs)
