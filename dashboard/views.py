"""
App Dashboard - Vues
KPIs, Graphiques, Rapports
"""

from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, ListView
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, Count, F, Q, Avg
from django.db.models.functions import TruncMonth, TruncWeek, TruncDay
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.decorators import login_required

from produits.models import Produit, Fournisseur, CategorieProduit
from mouvements.models import MouvementStock, BonEntree, BonSortie
from approvisionnement.models import CommandeAchat, SuggestionAppro
from .models import RapportSauvegarde, KPISnapshot

import json
from decimal import Decimal
from datetime import timedelta


# ============================================================
# TABLEAU DE BORD PRINCIPAL
# ============================================================

class DashboardIndexView(LoginRequiredMixin, TemplateView):
    """
    Tableau de bord principal — Vue exécutive StockPro.
    KPIs temps réel + graphiques + alertes.
    """
    template_name = 'dashboard/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        debut_mois = today.replace(day=1)

        # ---- KPIs Produits ----
        produits_actifs = Produit.objects.filter(statut='ACTIF')
        context['kpi_nb_references'] = produits_actifs.count()
        context['kpi_nb_ruptures'] = produits_actifs.filter(stock_actuel__lte=0).count()
        context['kpi_nb_alertes'] = produits_actifs.filter(
            stock_actuel__gt=0,
            stock_actuel__lte=F('stock_minimum'),
        ).count()
        context['kpi_valeur_stock'] = produits_actifs.aggregate(
            total=Sum(F('stock_actuel') * F('prix_unitaire_revient'))
        )['total'] or Decimal('0')

        # ---- KPIs Péremptions ----
        date_alerte_peremption = today + timedelta(days=90)
        context['kpi_peremptions_proches'] = 0  # À implémenter avec LotProduit

        # ---- KPIs Mouvements du mois ----
        context['kpi_entrees_mois'] = MouvementStock.objects.filter(
            type_mouvement=MouvementStock.TypeMouvement.ENTREE,
            statut=MouvementStock.StatutMouvement.VALIDE,
            date_mouvement__date__gte=debut_mois,
        ).aggregate(total=Sum('quantite'))['total'] or 0

        context['kpi_sorties_mois'] = MouvementStock.objects.filter(
            type_mouvement=MouvementStock.TypeMouvement.SORTIE,
            statut=MouvementStock.StatutMouvement.VALIDE,
            date_mouvement__date__gte=debut_mois,
        ).aggregate(total=Sum('quantite'))['total'] or 0

        # ---- KPIs Commandes ----
        context['kpi_commandes_en_attente'] = CommandeAchat.objects.filter(
            statut=CommandeAchat.Statut.EN_ATTENTE_VALIDATION
        ).count()
        context['kpi_suggestions_nouvelles'] = SuggestionAppro.objects.filter(
            statut=SuggestionAppro.Statut.NOUVELLE
        ).count()

        # ---- Alertes critiques ----
        context['produits_rupture'] = produits_actifs.filter(
            stock_actuel__lte=0
        ).select_related('categorie', 'unite_stock')[:10]

        context['produits_alerte'] = produits_actifs.filter(
            stock_actuel__gt=0,
            stock_actuel__lte=F('stock_minimum'),
        ).select_related('categorie', 'unite_stock')[:10]

        # ---- Mouvements récents ----
        context['mouvements_recents'] = MouvementStock.objects.filter(
            statut=MouvementStock.StatutMouvement.VALIDE
        ).select_related('produit', 'cree_par').order_by('-date_mouvement')[:8]

        # ---- Suggestions urgentes ----
        context['suggestions_urgentes'] = SuggestionAppro.objects.filter(
            statut=SuggestionAppro.Statut.NOUVELLE,
            urgente=True,
        ).select_related('produit', 'fournisseur')[:5]

        return context


# ============================================================
# API GRAPHIQUES (JSON)
# ============================================================

@login_required
def api_graphique_mouvements(request):
    """
    API : Évolution des mouvements entrées/sorties sur 30 jours.
    Pour Chart.js.
    """
    jours = int(request.GET.get('jours', 30))
    debut = timezone.now() - timedelta(days=jours)

    entrees = (
        MouvementStock.objects
        .filter(type_mouvement='ENTREE', statut='VALIDE', date_mouvement__gte=debut)
        .annotate(jour=TruncDay('date_mouvement'))
        .values('jour')
        .annotate(total=Sum('quantite'))
        .order_by('jour')
    )
    sorties = (
        MouvementStock.objects
        .filter(type_mouvement='SORTIE', statut='VALIDE', date_mouvement__gte=debut)
        .annotate(jour=TruncDay('date_mouvement'))
        .values('jour')
        .annotate(total=Sum('quantite'))
        .order_by('jour')
    )

    return JsonResponse({
        'entrees': [{'date': str(e['jour'].date()), 'total': float(e['total'] or 0)} for e in entrees],
        'sorties': [{'date': str(s['jour'].date()), 'total': float(s['total'] or 0)} for s in sorties],
    })


@login_required
def api_graphique_valorisation_categories(request):
    """
    API : Valorisation du stock par catégorie (pour graphique camembert).
    """
    data = (
        Produit.objects
        .filter(statut='ACTIF')
        .values('categorie__libelle', 'categorie__couleur')
        .annotate(valeur=Sum(F('stock_actuel') * F('prix_unitaire_revient')))
        .order_by('-valeur')[:10]
    )
    return JsonResponse({
        'labels': [d['categorie__libelle'] or 'Non classifié' for d in data],
        'valeurs': [float(d['valeur'] or 0) for d in data],
        'couleurs': [d['categorie__couleur'] or '#0d6efd' for d in data],
    })


@login_required
def api_graphique_abc(request):
    """
    API : Distribution ABC des produits.
    """
    counts = (
        Produit.objects
        .filter(statut='ACTIF')
        .values('classe_abc')
        .annotate(
            count=Count('id'),
            valeur=Sum(F('stock_actuel') * F('prix_unitaire_revient'))
        )
        .order_by('classe_abc')
    )
    return JsonResponse({
        'data': [
            {
                'classe': d['classe_abc'],
                'count': d['count'],
                'valeur': float(d['valeur'] or 0),
            }
            for d in counts
        ]
    })


@login_required
def api_kpis_temps_reel(request):
    """
    API : KPIs en temps réel pour rafraîchissement AJAX.
    """
    produits_actifs = Produit.objects.filter(statut='ACTIF')
    return JsonResponse({
        'nb_ruptures': produits_actifs.filter(stock_actuel__lte=0).count(),
        'nb_alertes': produits_actifs.filter(
            stock_actuel__gt=0, stock_actuel__lte=F('stock_minimum')
        ).count(),
        'nb_suggestions': SuggestionAppro.objects.filter(statut='NOUVELLE').count(),
        'nb_commandes_attente': CommandeAchat.objects.filter(statut='VALIDATION').count(),
        'valeur_stock': float(
            produits_actifs.aggregate(
                total=Sum(F('stock_actuel') * F('prix_unitaire_revient'))
            )['total'] or 0
        ),
    })


# ============================================================
# RAPPORTS
# ============================================================

class RapportIndexView(LoginRequiredMixin, TemplateView):
    """Page des rapports disponibles."""
    template_name = 'dashboard/rapports/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['rapports_recents'] = RapportSauvegarde.objects.filter(
            cree_par=self.request.user
        ).order_by('-date_creation')[:10]
        return context


@login_required
def generer_rapport_stock(request):
    """Générer un rapport PDF du stock actuel."""
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    import io
    from django.conf import settings

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=1*cm, leftMargin=1*cm)
    styles = getSampleStyleSheet()
    story = []

    # Titre
    story.append(Paragraph(
        f"<b>RAPPORT DE STOCK — {settings.COMPANY_INFO['nom'].upper()}</b>",
        styles['Title']
    ))
    story.append(Paragraph(
        f"Édité le : {timezone.now().strftime('%d/%m/%Y à %H:%M')} | "
        f"Par : {request.user.get_full_name() or request.user.username}",
        styles['Normal']
    ))
    story.append(Spacer(1, 0.5*cm))

    # Données
    produits = Produit.objects.filter(statut='ACTIF').select_related('categorie', 'unite_stock').order_by('designation')

    data = [['Code', 'Désignation', 'Catégorie', 'Stock actuel', 'Stock min.', 'Unité', 'Prix u.', 'Valeur (DH)', 'Statut']]
    for p in produits:
        statut_txt = {'rupture': '🔴 Rupture', 'alerte': '⚠️ Alerte', 'surstock': '📈 Surstock', 'normal': '✅ OK'}.get(p.statut_stock, '-')
        data.append([
            p.code,
            p.designation[:35],
            str(p.categorie),
            f"{p.stock_actuel:.2f}",
            f"{p.stock_minimum:.2f}",
            p.unite_stock.code,
            f"{p.prix_unitaire_revient:.2f}",
            f"{p.valeur_stock:,.2f}",
            statut_txt,
        ])

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0d6efd')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('ALIGN', (3, 0), (7, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    story.append(table)
    doc.build(story)
    buffer.seek(0)

    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="rapport_stock_{timezone.now().strftime("%Y%m%d")}.pdf"'
    return response


class AnalyseABCView(LoginRequiredMixin, TemplateView):
    """Analyse ABC — Classification des produits par valeur de consommation."""
    template_name = 'dashboard/rapports/analyse_abc.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        produits = Produit.objects.filter(statut='ACTIF').select_related('categorie', 'unite_stock')
        context['produits_a'] = produits.filter(classe_abc='A')
        context['produits_b'] = produits.filter(classe_abc='B')
        context['produits_c'] = produits.filter(classe_abc='C')
        context['nb_total'] = produits.count()
        return context
