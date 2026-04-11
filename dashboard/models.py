"""
App Dashboard - Modèles
Rapports sauvegardés, tableaux de bord personnalisés
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from core.models import ModeleBase


class RapportSauvegarde(ModeleBase):
    """Rapport généré et sauvegardé en base."""

    class TypeRapport(models.TextChoices):
        STOCK = 'STOCK', _('Rapport de stock')
        MOUVEMENTS = 'MVTS', _('Rapport des mouvements')
        VALORISATION = 'VALOR', _('Valorisation du stock')
        PEREMPTIONS = 'PEREMS', _('Alertes péremptions')
        COMMANDES = 'CMDS', _('Rapport des commandes')
        ABC = 'ABC', _('Analyse ABC')
        KPI = 'KPI', _('Indicateurs KPI')

    nom = models.CharField(max_length=200, verbose_name=_('Nom du rapport'))
    type_rapport = models.CharField(
        max_length=10,
        choices=TypeRapport.choices,
        verbose_name=_('Type de rapport'),
    )
    parametres = models.JSONField(
        default=dict,
        verbose_name=_('Paramètres de génération'),
    )
    fichier = models.FileField(
        upload_to='rapports/',
        null=True,
        blank=True,
        verbose_name=_('Fichier généré'),
    )
    genere_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_('Généré par'),
    )
    date_generation = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Date de génération'),
    )
    periode_debut = models.DateField(null=True, blank=True, verbose_name=_('Période du'))
    periode_fin = models.DateField(null=True, blank=True, verbose_name=_('Au'))

    class Meta:
        verbose_name = _('Rapport sauvegardé')
        verbose_name_plural = _('Rapports sauvegardés')
        ordering = ['-date_generation']

    def __str__(self):
        return f"{self.nom} — {self.date_generation.strftime('%d/%m/%Y')}"


class KPISnapshot(models.Model):
    """
    Snapshot quotidien des KPIs pour les graphiques historiques.
    Créé via une tâche Celery chaque jour.
    """
    date = models.DateField(unique=True, verbose_name=_('Date'))
    nb_references_actives = models.IntegerField(default=0, verbose_name=_('Références actives'))
    nb_ruptures = models.IntegerField(default=0, verbose_name=_('Ruptures de stock'))
    nb_alertes = models.IntegerField(default=0, verbose_name=_('Alertes stock'))
    nb_peremptions_proches = models.IntegerField(default=0, verbose_name=_('Péremptions < 90 jours'))
    valeur_stock_total = models.DecimalField(
        max_digits=16, decimal_places=2, default=0,
        verbose_name=_('Valeur totale stock (DH)'),
    )
    nb_commandes_en_cours = models.IntegerField(default=0)
    montant_commandes_en_cours = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    taux_service = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        verbose_name=_('Taux de service (%)'),
    )
    taux_rotation = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        verbose_name=_('Taux de rotation'),
    )

    class Meta:
        verbose_name = _('Snapshot KPI')
        verbose_name_plural = _('Snapshots KPI')
        ordering = ['-date']

    def __str__(self):
        return f"KPI du {self.date}"
