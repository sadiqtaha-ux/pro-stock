"""
App Approvisionnement - Modèles
4 méthodes : REAPPRO_FIXE, POINT_COMMANDE, RECOMPLETEMENT, MRP
Commandes d'achat, suggestions, plans MRP
MediCare Industries - StockPro
"""

import math
from django.db import models
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.conf import settings

from core.models import ModeleBase


# ============================================================
# MÉTHODES D'APPROVISIONNEMENT
# ============================================================

class MethodeApprovisionnement(models.TextChoices):
    """
    Les 4 méthodes d'approvisionnement supportées par StockPro.

    1. REAPPRO_FIXE : Réapprovisionnement à quantité et période fixes
       → Commander une quantité Q fixe toutes les T périodes
       → Adapté aux produits à consommation régulière

    2. POINT_COMMANDE (ROP - Reorder Point) :
       → Déclencher une commande quand le stock descend sous un seuil
       → Seuil = Consommation journalière × Délai réappro + Stock sécu
       → Adapté aux produits à forte valeur ou consommation variable

    3. RECOMPLETEMENT (S,T - Stock cible) :
       → Révision périodique, commander jusqu'à atteindre S (stock cible)
       → Quantité commandée = S - Stock actuel
       → Adapté aux produits périssables ou à faible valeur

    4. MRP (Material Requirements Planning) :
       → Planification des besoins en matières selon le programme de production
       → Calcul : Besoins bruts → Besoins nets → Ordres proposés
       → Adapté à la production pharmaceutique planifiée
    """
    REAPPRO_FIXE = 'REAPPRO_FIXE', _('Réapprovisionnement à quantité fixe')
    POINT_COMMANDE = 'POINT_COMMANDE', _('Point de commande (ROP)')
    RECOMPLETEMENT = 'RECOMPLETEMENT', _('Récompletement périodique (S,T)')
    MRP = 'MRP', _('MRP — Calcul des besoins en matières')


# ============================================================
# PARAMÈTRES D'APPROVISIONNEMENT PAR PRODUIT
# ============================================================

class ParametreAppro(ModeleBase):
    """
    Paramètres d'approvisionnement spécifiques à chaque produit/méthode.
    Centralise tous les paramètres nécessaires aux calculs.
    """
    produit = models.OneToOneField(
        'produits.Produit',
        on_delete=models.CASCADE,
        related_name='parametre_appro',
        verbose_name=_('Produit'),
    )
    methode = models.CharField(
        max_length=20,
        choices=MethodeApprovisionnement.choices,
        verbose_name=_('Méthode d\'approvisionnement'),
    )

    # Paramètres communs
    consommation_journaliere_moyenne = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=0,
        verbose_name=_('Consommation journalière moyenne (CJM)'),
    )
    ecart_type_consommation = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=0,
        verbose_name=_('Écart-type de la consommation'),
    )
    delai_reappro_jours = models.PositiveIntegerField(
        default=7,
        verbose_name=_('Délai de réapprovisionnement (jours)'),
    )
    niveau_service = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=95.00,
        verbose_name=_('Niveau de service cible (%)'),
    )
    cout_possession = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=20.00,
        verbose_name=_('Coût de possession (% valeur/an)'),
    )
    cout_passation = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=50.00,
        verbose_name=_('Coût de passation de commande (DH)'),
    )

    # Méthode 1 : REAPPRO_FIXE
    quantite_commande_fixe = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
        verbose_name=_('[FIXE] Quantité de commande fixe Q'),
    )
    periodicite_commande = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_('[FIXE] Périodicité de commande (jours)'),
    )
    date_prochaine_commande = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('[FIXE] Date de prochaine commande'),
    )

    # Méthode 2 : POINT_COMMANDE (ROP)
    point_commande_calcule = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
        verbose_name=_('[ROP] Point de commande calculé'),
    )
    stock_securite_calcule = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
        verbose_name=_('[ROP] Stock de sécurité calculé'),
    )
    qec_calcule = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
        verbose_name=_('[ROP] QEC calculée (Wilson)'),
    )

    # Méthode 3 : RECOMPLETEMENT
    stock_cible = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
        verbose_name=_('[S,T] Stock cible S'),
    )
    periode_revision = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_('[S,T] Période de révision T (jours)'),
    )

    # Méthode 4 : MRP
    nomenclature_coefficient = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        default=1,
        verbose_name=_('[MRP] Coefficient de nomenclature'),
    )
    lot_multiple = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
        verbose_name=_('[MRP] Lot multiple / Taille de lot'),
    )
    horizon_planification = models.PositiveIntegerField(
        default=12,
        verbose_name=_('[MRP] Horizon de planification (semaines)'),
    )

    # Résultats calculés
    date_derniere_maj = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Dernière mise à jour'),
    )

    class Meta:
        verbose_name = _('Paramètre d\'approvisionnement')
        verbose_name_plural = _('Paramètres d\'approvisionnement')

    def __str__(self):
        return f"{self.produit.code} — {self.get_methode_display()}"

    # ---- Calculs automatiques ----

    def calculer_qec_wilson(self):
        """
        Formule de Wilson (EOQ) :
        QEC = sqrt( 2 × D × K / (h × Pu) )
        D = demande annuelle, K = coût passation, h = taux possession, Pu = prix unitaire
        """
        D = float(self.consommation_journaliere_moyenne) * 365
        K = float(self.cout_passation)
        h = float(self.cout_possession) / 100
        Pu = float(self.produit.prix_unitaire_revient or 1)
        if D > 0 and h > 0 and Pu > 0:
            qec = math.sqrt(2 * D * K / (h * Pu))
            self.qec_calcule = round(qec, 3)
        return self.qec_calcule

    def calculer_stock_securite(self, z_score=1.645):
        """
        Stock de sécurité = z × σ × sqrt(L)
        z = facteur de sécurité, σ = écart-type consommation, L = délai réappro
        z=1.645 pour un niveau de service de 95%
        """
        sigma = float(self.ecart_type_consommation)
        L = float(self.delai_reappro_jours)
        ss = z_score * sigma * math.sqrt(L)
        self.stock_securite_calcule = round(ss, 3)
        return self.stock_securite_calcule

    def calculer_point_commande(self):
        """
        Point de commande = CJM × Délai + Stock sécurité
        """
        cjm = float(self.consommation_journaliere_moyenne)
        L = float(self.delai_reappro_jours)
        ss = float(self.stock_securite_calcule or self.calculer_stock_securite())
        rop = cjm * L + ss
        self.point_commande_calcule = round(rop, 3)
        return self.point_commande_calcule

    def calculer_stock_cible_recompletement(self):
        """
        Stock cible S = CJM × (T + L) + Stock sécurité
        T = période de révision, L = délai réappro
        """
        cjm = float(self.consommation_journaliere_moyenne)
        T = float(self.periode_revision or 30)
        L = float(self.delai_reappro_jours)
        ss = float(self.stock_securite_calcule or 0)
        s = cjm * (T + L) + ss
        self.stock_cible = round(s, 3)
        return self.stock_cible


# ============================================================
# COMMANDE D'ACHAT
# ============================================================

class CommandeAchat(ModeleBase):
    """
    Bon de commande d'approvisionnement fournisseur.
    Généré manuellement ou automatiquement par les méthodes.
    """

    class Statut(models.TextChoices):
        BROUILLON = 'BROUILLON', _('Brouillon')
        EN_ATTENTE_VALIDATION = 'VALIDATION', _('En attente de validation')
        VALIDE = 'VALIDE', _('Validée')
        ENVOYE = 'ENVOYE', _('Envoyée au fournisseur')
        PARTIELLEMENT_RECU = 'PARTIEL', _('Partiellement réceptionnée')
        TOTALEMENT_RECU = 'RECU', _('Totalement réceptionnée')
        ANNULE = 'ANNULE', _('Annulée')
        CLOTURE = 'CLOTURE', _('Clôturée')

    class TypeCommande(models.TextChoices):
        NORMALE = 'NORMALE', _('Commande normale')
        URGENTE = 'URGENTE', _('Commande urgente')
        AUTOMATIQUE = 'AUTO', _('Générée automatiquement')
        MRP = 'MRP', _('Ordre MRP')

    # Identification
    numero = models.CharField(
        max_length=20,
        unique=True,
        verbose_name=_('N° de commande'),
    )
    fournisseur = models.ForeignKey(
        'produits.Fournisseur',
        on_delete=models.PROTECT,
        related_name='commandes',
        verbose_name=_('Fournisseur'),
    )
    statut = models.CharField(
        max_length=20,
        choices=Statut.choices,
        default=Statut.BROUILLON,
        verbose_name=_('Statut'),
    )
    type_commande = models.CharField(
        max_length=20,
        choices=TypeCommande.choices,
        default=TypeCommande.NORMALE,
        verbose_name=_('Type de commande'),
    )
    methode_declenchement = models.CharField(
        max_length=20,
        choices=MethodeApprovisionnement.choices,
        null=True,
        blank=True,
        verbose_name=_('Méthode de déclenchement'),
    )

    # Dates
    date_commande = models.DateField(
        default=timezone.now,
        verbose_name=_('Date de commande'),
    )
    date_livraison_prevue = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Date de livraison prévue'),
    )
    date_livraison_reelle = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Date de livraison réelle'),
    )

    # Montants
    montant_ht = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name=_('Montant HT (DH)'),
    )
    montant_tva = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name=_('Montant TVA (DH)'),
    )
    montant_ttc = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name=_('Montant TTC (DH)'),
    )

    # Validation
    valide_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='commandes_validees',
        verbose_name=_('Validé par'),
    )
    date_validation = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, verbose_name=_('Notes'))
    conditions_paiement = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Conditions de paiement'),
    )

    class Meta:
        verbose_name = _('Commande d\'achat')
        verbose_name_plural = _('Commandes d\'achat')
        ordering = ['-date_commande']
        indexes = [
            models.Index(fields=['statut']),
            models.Index(fields=['fournisseur', 'statut']),
        ]

    def __str__(self):
        return f"{self.numero} — {self.fournisseur.raison_sociale} — {self.montant_ttc:.2f} DH"

    def save(self, *args, **kwargs):
        if not self.numero:
            annee = timezone.now().strftime('%Y%m')
            count = CommandeAchat.objects.count() + 1
            self.numero = f"BC-{annee}-{count:05d}"
        super().save(*args, **kwargs)

    def recalculer_montants(self):
        """Recalculer les montants depuis les lignes."""
        total_ht = sum(ligne.montant_ht for ligne in self.lignes.all())
        total_tva = sum(ligne.montant_tva for ligne in self.lignes.all())
        self.montant_ht = total_ht
        self.montant_tva = total_tva
        self.montant_ttc = total_ht + total_tva
        self.save(update_fields=['montant_ht', 'montant_tva', 'montant_ttc'])


# ============================================================
# LIGNE DE COMMANDE D'ACHAT
# ============================================================

class LigneCommandeAchat(models.Model):
    """Ligne détail d'une commande d'achat."""

    commande = models.ForeignKey(
        CommandeAchat,
        on_delete=models.CASCADE,
        related_name='lignes',
        verbose_name=_('Commande'),
    )
    produit = models.ForeignKey(
        'produits.Produit',
        on_delete=models.PROTECT,
        related_name='lignes_commande',
        verbose_name=_('Produit'),
    )
    quantite_commandee = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        validators=[MinValueValidator(0.001)],
        verbose_name=_('Quantité commandée'),
    )
    quantite_recue = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0,
        verbose_name=_('Quantité reçue'),
    )
    unite = models.ForeignKey(
        'produits.UniteMesure',
        on_delete=models.PROTECT,
        verbose_name=_('Unité'),
    )
    prix_unitaire_ht = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        verbose_name=_('Prix unitaire HT'),
    )
    remise = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name=_('Remise (%)'),
    )
    tva = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=20,
        verbose_name=_('TVA (%)'),
    )
    date_livraison_souhaitee = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Date de livraison souhaitée'),
    )

    class Meta:
        verbose_name = _('Ligne de commande')
        verbose_name_plural = _('Lignes de commande')

    def __str__(self):
        return f"{self.commande.numero} / {self.produit.code}"

    @property
    def prix_net_ht(self):
        return float(self.prix_unitaire_ht) * (1 - float(self.remise) / 100)

    @property
    def montant_ht(self):
        return self.quantite_commandee * self.prix_net_ht

    @property
    def montant_tva(self):
        return float(self.montant_ht) * float(self.tva) / 100

    @property
    def montant_ttc(self):
        return float(self.montant_ht) + self.montant_tva

    @property
    def quantite_restante(self):
        return max(0, float(self.quantite_commandee) - float(self.quantite_recue))


# ============================================================
# SUGGESTION D'APPROVISIONNEMENT
# ============================================================

class SuggestionAppro(ModeleBase):
    """
    Suggestion de commande générée automatiquement
    par les algorithmes d'approvisionnement.
    """

    class Statut(models.TextChoices):
        NOUVELLE = 'NOUVELLE', _('Nouvelle')
        ACCEPTEE = 'ACCEPTEE', _('Acceptée')
        REJETEE = 'REJETEE', _('Rejetée')
        TRANSFORMEE = 'TRANSFORMEE', _('Transformée en commande')

    produit = models.ForeignKey(
        'produits.Produit',
        on_delete=models.CASCADE,
        related_name='suggestions',
        verbose_name=_('Produit'),
    )
    fournisseur = models.ForeignKey(
        'produits.Fournisseur',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('Fournisseur suggéré'),
    )
    methode = models.CharField(
        max_length=20,
        choices=MethodeApprovisionnement.choices,
        verbose_name=_('Méthode de calcul'),
    )
    quantite_suggeree = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        verbose_name=_('Quantité suggérée'),
    )
    date_suggestion = models.DateField(
        default=timezone.now,
        verbose_name=_('Date de suggestion'),
    )
    date_commande_prevue = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Date de commande prévue'),
    )
    date_livraison_prevue = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Date de livraison prévue'),
    )
    statut = models.CharField(
        max_length=20,
        choices=Statut.choices,
        default=Statut.NOUVELLE,
        verbose_name=_('Statut'),
    )
    stock_au_moment = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0,
        verbose_name=_('Stock au moment du calcul'),
    )
    justification = models.TextField(
        blank=True,
        verbose_name=_('Justification du calcul'),
    )
    commande_generee = models.ForeignKey(
        CommandeAchat,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='suggestions_origine',
        verbose_name=_('Commande générée'),
    )
    urgente = models.BooleanField(
        default=False,
        verbose_name=_('Urgente'),
    )

    class Meta:
        verbose_name = _('Suggestion d\'approvisionnement')
        verbose_name_plural = _('Suggestions d\'approvisionnement')
        ordering = ['-date_suggestion', '-urgente']

    def __str__(self):
        return f"Suggestion {self.produit.code} — {self.quantite_suggeree} {self.produit.unite_stock.code}"


# ============================================================
# PLAN MRP
# ============================================================

class PlanMRP(ModeleBase):
    """
    Plan MRP (Material Requirements Planning).
    Planification des besoins en matières.
    """

    class Statut(models.TextChoices):
        CALCUL_EN_COURS = 'CALCUL', _('Calcul en cours')
        CALCULE = 'CALCULE', _('Calculé')
        APPROUVE = 'APPROUVE', _('Approuvé')
        EN_COURS = 'EN_COURS', _('En cours d\'exécution')
        TERMINE = 'TERMINE', _('Terminé')
        ANNULE = 'ANNULE', _('Annulé')

    numero = models.CharField(max_length=20, unique=True, verbose_name=_('N° plan MRP'))
    description = models.CharField(max_length=200, verbose_name=_('Description'))
    date_debut = models.DateField(verbose_name=_('Date de début'))
    date_fin = models.DateField(verbose_name=_('Date de fin'))
    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.CALCUL_EN_COURS)
    horizon_semaines = models.PositiveIntegerField(default=12, verbose_name=_('Horizon (semaines)'))
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = _('Plan MRP')
        verbose_name_plural = _('Plans MRP')
        ordering = ['-date_debut']

    def __str__(self):
        return f"{self.numero} — {self.description}"

    def save(self, *args, **kwargs):
        if not self.numero:
            annee = timezone.now().strftime('%Y%m')
            count = PlanMRP.objects.count() + 1
            self.numero = f"MRP-{annee}-{count:04d}"
        super().save(*args, **kwargs)


class LigneMRP(models.Model):
    """
    Ligne de plan MRP : besoins bruts, nets, ordres proposés
    pour un produit sur un horizon donné.
    """
    plan = models.ForeignKey(
        PlanMRP,
        on_delete=models.CASCADE,
        related_name='lignes',
        verbose_name=_('Plan MRP'),
    )
    produit = models.ForeignKey(
        'produits.Produit',
        on_delete=models.CASCADE,
        related_name='lignes_mrp',
        verbose_name=_('Produit'),
    )
    semaine = models.PositiveSmallIntegerField(verbose_name=_('Semaine'))
    annee = models.PositiveSmallIntegerField(verbose_name=_('Année'))
    besoin_brut = models.DecimalField(
        max_digits=12, decimal_places=3, default=0,
        verbose_name=_('Besoin brut (BB)'),
    )
    reception_programmee = models.DecimalField(
        max_digits=12, decimal_places=3, default=0,
        verbose_name=_('Réception programmée (RP)'),
    )
    stock_disponible = models.DecimalField(
        max_digits=12, decimal_places=3, default=0,
        verbose_name=_('Stock disponible projeté'),
    )
    besoin_net = models.DecimalField(
        max_digits=12, decimal_places=3, default=0,
        verbose_name=_('Besoin net (BN)'),
    )
    ordre_propose = models.DecimalField(
        max_digits=12, decimal_places=3, default=0,
        verbose_name=_('Ordre proposé (OP)'),
    )
    ordre_lance = models.DecimalField(
        max_digits=12, decimal_places=3, default=0,
        verbose_name=_('Ordre lancé'),
    )

    class Meta:
        verbose_name = _('Ligne MRP')
        verbose_name_plural = _('Lignes MRP')
        unique_together = ['plan', 'produit', 'semaine', 'annee']
        ordering = ['annee', 'semaine']

    def __str__(self):
        return f"{self.plan.numero} / {self.produit.code} S{self.semaine}-{self.annee}"

    def calculer_besoin_net(self):
        """BN = max(0, BB - RP - Stock disponible)"""
        self.besoin_net = max(
            0,
            float(self.besoin_brut) - float(self.reception_programmee) - float(self.stock_disponible)
        )
        return self.besoin_net
