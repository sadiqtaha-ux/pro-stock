"""
dashboard/views.py
MediCare Industries — KPIs, Graphiques, Rapports
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, Count, F, Q
from django.db.models.functions import TruncDay
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from decimal import Decimal
from datetime import timedelta

from produits.models import MatierePremiere
from mouvements.models import MouvementStock
from approvisionnement.models import BonCommande
from .models import RapportSauvegarde, KPISnapshot


# ============================================================
# TABLEAU DE BORD PRINCIPAL
# ============================================================

class DashboardIndexView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/index.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today      = timezone.now().date()
        debut_mois = today.replace(day=1)

        # KPIs matières
        matieres_actives = MatierePremiere.objects.filter(actif=True)
        ctx["kpi_nb_references"] = matieres_actives.count()
        ctx["kpi_nb_ruptures"]   = matieres_actives.filter(stock_actuel__lte=0).count()
        ctx["kpi_nb_alertes"]    = matieres_actives.filter(
            stock_actuel__gt=0,
            stock_actuel__lte=F("stock_minimum"),
        ).count()
        ctx["kpi_valeur_stock"]  = matieres_actives.aggregate(
            total=Sum(F("stock_actuel") * F("prix_unitaire"))
        )["total"] or Decimal("0")

        # KPIs mouvements du mois
        mvts_mois = MouvementStock.objects.filter(date_mouvement__date__gte=debut_mois)
        ctx["kpi_entrees_mois"] = mvts_mois.filter(
            type_mouvement=MouvementStock.TypeMouvement.ENTREE
        ).aggregate(total=Sum("quantite"))["total"] or 0
        ctx["kpi_sorties_mois"] = mvts_mois.filter(
            type_mouvement=MouvementStock.TypeMouvement.SORTIE
        ).aggregate(total=Sum("quantite"))["total"] or 0

        # KPIs commandes
        ctx["kpi_commandes_en_attente"] = BonCommande.objects.filter(
            statut=BonCommande.Statut.BROUILLON
        ).count()

        # Alertes critiques
        ctx["matieres_rupture"] = matieres_actives.filter(
            stock_actuel__lte=0
        ).select_related("unite")[:10]

        ctx["matieres_alerte"] = matieres_actives.filter(
            stock_actuel__gt=0,
            stock_actuel__lte=F("stock_minimum"),
        ).select_related("unite")[:10]

        # Mouvements récents
        ctx["mouvements_recents"] = MouvementStock.objects.select_related(
            "matiere", "operateur"
        ).order_by("-date_mouvement")[:8]

        # Commandes récentes
        ctx["commandes_recentes"] = BonCommande.objects.select_related(
            "matiere", "fournisseur"
        ).order_by("-date_creation")[:5]

        return ctx


# ============================================================
# API GRAPHIQUES (JSON pour Chart.js)
# ============================================================

@login_required
def api_graphique_mouvements(request):
    """Évolution entrées / sorties sur N jours."""
    jours = int(request.GET.get("jours", 30))
    debut = timezone.now() - timedelta(days=jours)

    entrees = (
        MouvementStock.objects
        .filter(type_mouvement="ENTREE", date_mouvement__gte=debut)
        .annotate(jour=TruncDay("date_mouvement"))
        .values("jour")
        .annotate(total=Sum("quantite"))
        .order_by("jour")
    )
    sorties = (
        MouvementStock.objects
        .filter(type_mouvement="SORTIE", date_mouvement__gte=debut)
        .annotate(jour=TruncDay("date_mouvement"))
        .values("jour")
        .annotate(total=Sum("quantite"))
        .order_by("jour")
    )
    return JsonResponse({
        "entrees": [{"date": str(e["jour"].date()), "total": float(e["total"] or 0)} for e in entrees],
        "sorties": [{"date": str(s["jour"].date()), "total": float(s["total"] or 0)} for s in sorties],
    })


@login_required
def api_graphique_valorisation(request):
    """Valorisation du stock par catégorie (camembert)."""
    COULEURS = {
        "PRINCIPE_ACTIF":  "#0d6efd",
        "EXCIPIENT":       "#198754",
        "CONDITIONNEMENT": "#ffc107",
    }
    data = (
        MatierePremiere.objects
        .filter(actif=True)
        .values("categorie")
        .annotate(valeur=Sum(F("stock_actuel") * F("prix_unitaire")))
        .order_by("-valeur")
    )
    labels  = [d["categorie"] for d in data]
    valeurs = [float(d["valeur"] or 0) for d in data]
    couleurs = [COULEURS.get(d["categorie"], "#6c757d") for d in data]
    return JsonResponse({"labels": labels, "valeurs": valeurs, "couleurs": couleurs})


@login_required
def api_kpis(request):
    """KPIs temps réel — rafraîchissement AJAX."""
    matieres = MatierePremiere.objects.filter(actif=True)
    return JsonResponse({
        "nb_ruptures":          matieres.filter(stock_actuel__lte=0).count(),
        "nb_alertes":           matieres.filter(stock_actuel__gt=0, stock_actuel__lte=F("stock_minimum")).count(),
        "nb_commandes_attente": BonCommande.objects.filter(statut=BonCommande.Statut.BROUILLON).count(),
        "valeur_stock":         float(
            matieres.aggregate(total=Sum(F("stock_actuel") * F("prix_unitaire")))["total"] or 0
        ),
    })


# ============================================================
# RAPPORTS
# ============================================================

class RapportIndexView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/rapports/index.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["rapports_recents"] = RapportSauvegarde.objects.filter(
            cree_par=self.request.user
        ).order_by("-date_creation")[:10]
        return ctx


@login_required
def generer_rapport_stock(request):
    """Rapport PDF du stock actuel (ReportLab)."""
    import io
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from django.conf import settings

    buffer = io.BytesIO()
    doc    = SimpleDocTemplate(buffer, pagesize=landscape(A4),
                               rightMargin=1*cm, leftMargin=1*cm)
    styles = getSampleStyleSheet()
    story  = []

    story.append(Paragraph(
        f"<b>RAPPORT DE STOCK — {settings.COMPANY_INFO['nom'].upper()}</b>",
        styles["Title"]
    ))
    story.append(Paragraph(
        f"Édité le : {timezone.now().strftime('%d/%m/%Y à %H:%M')} | "
        f"Par : {request.user.get_full_name() or request.user.username}",
        styles["Normal"]
    ))
    story.append(Spacer(1, 0.5*cm))

    matieres = MatierePremiere.objects.filter(actif=True).select_related(
        "unite", "fournisseur_principal"
    ).order_by("reference")

    entete = [["Référence", "Nom", "Catégorie", "Stock actuel", "Stock min.", "Unité", "Prix u. (DH)", "Valeur (DH)"]]
    for m in matieres:
        entete.append([
            m.reference,
            m.nom[:40],
            m.get_categorie_display(),
            f"{m.stock_actuel:.3f}",
            f"{m.stock_minimum:.3f}",
            m.unite.symbole if m.unite else "—",
            f"{m.prix_unitaire:.4f}",
            f"{float(m.stock_actuel * m.prix_unitaire):,.2f}",
        ])

    table = Table(entete, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), colors.HexColor("#0d6efd")),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 7),
        ("ALIGN",         (3, 0), (-1, -1), "RIGHT"),
        ("GRID",          (0, 0), (-1, -1), 0.3, colors.grey),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
    ]))
    story.append(table)
    doc.build(story)
    buffer.seek(0)

    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="rapport_stock_{timezone.now().strftime("%Y%m%d")}.pdf"'
    )
    return response
