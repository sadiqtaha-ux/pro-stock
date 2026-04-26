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
        ENTREE      = "ENTREE",      _("Entrée")
        SORTIE      = "SORTIE",      _("Sortie")
        AJUSTEMENT  = "AJUSTEMENT",  _("Ajustement")
        TRANSFERT   = "TRANSFERT",   _("Transfert")

    # --- Article concerné : matière première OU produit fini ---
    matiere = models.ForeignKey(
        "produits.MatierePremiere",
        on_delete=models.PROTECT,
        related_name="mouvements",
        verbose_name=_("Matière première"),
        null=True, blank=True,
    )
    produit_fini = models.ForeignKey(
        "produits.ProduitFini",
        on_delete=models.PROTECT,
        related_name="mouvements",
        verbose_name=_("Produit fini"),
        null=True, blank=True,
    )
    # Type de stock pour filtrage rapide
    TYPE_STOCK_CHOICES = [
        ("MP", _("Matière première")),
        ("PF", _("Produit fini")),
    ]
    type_stock = models.CharField(
        _("Type de stock"), max_length=2,
        choices=TYPE_STOCK_CHOICES, default="MP"
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
            models.Index(fields=["produit_fini", "date_mouvement"]),
            models.Index(fields=["type_mouvement"]),
            models.Index(fields=["type_stock"]),
            models.Index(fields=["numero_lot"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(matiere__isnull=False, produit_fini__isnull=True) |
                    models.Q(matiere__isnull=True,  produit_fini__isnull=False)
                ),
                name="mouvementstock_matiere_ou_produit_fini",
            )
        ]

    def __str__(self):
        signe = "+" if self.type_mouvement == self.TypeMouvement.ENTREE else "-"
        article = self.matiere or self.produit_fini
        return f"{self.date_mouvement:%d/%m/%Y %H:%M} | {article} | {signe}{self.quantite}"

    def clean(self):
        from django.core.exceptions import ValidationError
        if not self.matiere and not self.produit_fini:
            raise ValidationError(_("Un mouvement doit concerner une matière première ou un produit fini."))
        if self.matiere and self.produit_fini:
            raise ValidationError(_("Un mouvement ne peut concerner qu'un seul type d'article."))
        # Auto-remplissage type_stock
        if self.matiere:
            self.type_stock = "MP"
        elif self.produit_fini:
            self.type_stock = "PF"

    def save(self, *args, **kwargs):
        """
        Garantit que le stock de l'article est mis à jour atomiquement
        lors de la création d'un nouveau mouvement.
        """
        from django.db import transaction
        
        # On ne traite la mise à jour automatique que pour les nouveaux mouvements
        is_new = self.pk is None
        
        if is_new:
            with transaction.atomic():
                article = self.matiere or self.produit_fini
                if article:
                    # Capture du stock actuel
                    self.quantite_avant = article.stock_actuel
                    
                    # Calcul de l'après selon le type
                    if self.type_mouvement == self.TypeMouvement.ENTREE:
                        self.quantite_apres = self.quantite_avant + self.quantite
                    elif self.type_mouvement == self.TypeMouvement.SORTIE:
                        self.quantite_apres = self.quantite_avant - self.quantite
                    elif self.type_mouvement == self.TypeMouvement.AJUSTEMENT:
                        # AJUSTEMENT : la quantité saisie devient le nouveau stock
                        self.quantite_apres = self.quantite
                    elif self.type_mouvement == self.TypeMouvement.TRANSFERT:
                        # Pour un transfert, on considère ici la sortie du stock source
                        # (La logique de réception sur destination peut être gérée ailleurs)
                        self.quantite_apres = self.quantite_avant - self.quantite
                    
                    # Mise à jour réelle du modèle d'article
                    article.stock_actuel = self.quantite_apres
                    article.save(update_fields=['stock_actuel'])
        
        super().save(*args, **kwargs)
