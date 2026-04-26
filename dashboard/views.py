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
from django.utils.translation import gettext as _

from produits.models import MatierePremiere, ProduitFini, Fournisseur
from mouvements.models import MouvementStock
from approvisionnement.models import BonCommande, PropositionCommande
from magasin.models import Emplacement, ZoneStockage
from .models import RapportSauvegarde, KPISnapshot


# ============================================================
# TABLEAU DE BORD PRINCIPAL
# ============================================================

class DashboardIndexView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/index.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = timezone.now().date()
        
        # --- 1. KPIs Principaux (Executive) ---
        matieres_actives = MatierePremiere.objects.filter(actif=True)
        produits_actifs = ProduitFini.objects.filter(actif=True)
        
        ctx["kpi_mp_total"] = matieres_actives.count()
        ctx["kpi_pf_total"] = produits_actifs.count()
        
        # Ruptures & Critiques (Global)
        ctx["kpi_ruptures"] = matieres_actives.filter(stock_actuel__lte=0).count() + produits_actifs.filter(stock_actuel__lte=0).count()
        ctx["kpi_critiques"] = matieres_actives.filter(stock_actuel__gt=0, stock_actuel__lte=F("stock_minimum")).count() + produits_actifs.filter(stock_actuel__gt=0, stock_actuel__lte=F("stock_minimum")).count()
        
        # Approvisionnement
        ctx["kpi_commandes_retard"] = BonCommande.objects.exclude(
            statut__in=[BonCommande.Statut.RECU, BonCommande.Statut.ANNULE]
        ).filter(date_reception_prevue__lt=today).count()
        ctx["kpi_propositions_valider"] = PropositionCommande.objects.filter(statut=PropositionCommande.Statut.EN_ATTENTE).count()
        
        # Magasin
        emplacements = Emplacement.objects.all()
        if emplacements.exists():
            ctx["kpi_mag_occupation"] = round((emplacements.filter(statut=Emplacement.StatutEmplacement.OCCUPE).count() / emplacements.count()) * 100, 1)
        else:
            ctx["kpi_mag_occupation"] = 0
            
        # Valeur Stock
        val_mp = matieres_actives.aggregate(total=Sum(F("stock_actuel") * F("prix_unitaire")))["total"] or Decimal("0")
        val_pf = produits_actifs.aggregate(total=Sum(F("stock_actuel") * F("prix_unitaire")))["total"] or Decimal("0")
        ctx["kpi_valeur_totale"] = val_mp + val_pf

        # --- 2. Actions Urgentes (Top Lists) ---
        ctx["top_mp_rupture"] = matieres_actives.filter(stock_actuel__lte=0)[:5]
        ctx["top_pf_rupture"] = produits_actifs.filter(stock_actuel__lte=0)[:5]
        ctx["cmd_retard_liste"] = BonCommande.objects.exclude(
            statut__in=[BonCommande.Statut.RECU, BonCommande.Statut.ANNULE]
        ).filter(date_reception_prevue__lt=today).order_by("date_reception_prevue")[:5]
        ctx["mrp_propositions"] = PropositionCommande.objects.filter(statut=PropositionCommande.Statut.EN_ATTENTE).order_by("-urgence")[:5]

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
    labels  = [dict(MatierePremiere.Categorie.choices).get(d["categorie"], d["categorie"]) for d in data]
    valeurs = [float(d["valeur"] or 0) for d in data]
    couleurs = [COULEURS.get(d["categorie"], "#6c757d") for d in data]
    return JsonResponse({"labels": labels, "valeurs": valeurs, "couleurs": couleurs})


@login_required
def api_graphique_stock_statut(request):
    """Répartition du stock MP par statut (Donut)."""
    matieres = MatierePremiere.objects.filter(actif=True)
    nb_rupture = matieres.filter(stock_actuel__lte=0).count()
    nb_critique = matieres.filter(stock_actuel__gt=0, stock_actuel__lte=F("stock_minimum")).count()
    nb_alerte = matieres.filter(stock_actuel__gt=F("stock_minimum"), stock_actuel__lte=F("point_commande")).count()
    nb_normal = matieres.filter(stock_actuel__gt=F("point_commande")).count()

    return JsonResponse({
        "labels": ["Rupture", "Critique", "Alerte", "Normal"],
        "valeurs": [nb_rupture, nb_critique, nb_alerte, nb_normal],
        "couleurs": ["#dc3545", "#fd7e14", "#ffc107", "#198754"]
    })


@login_required
def api_graphique_abc(request):
    """Répartition ABC (Bar)."""
    data = (
        MatierePremiere.objects
        .filter(actif=True)
        .values("classe_abc")
        .annotate(nb=Count("id"))
        .order_by("classe_abc")
    )
    labels = [d["classe_abc"] or "NC" for d in data]
    valeurs = [d["nb"] for d in data]
    return JsonResponse({
        "labels": labels,
        "valeurs": valeurs,
        "couleurs": ["#0d6efd", "#6610f2", "#6f42c1"]
    })


@login_required
def api_graphique_commandes_statut(request):
    """Répartition des commandes par statut (Bar)."""
    data = (
        BonCommande.objects
        .values("statut")
        .annotate(nb=Count("id"))
    )
    labels = [dict(BonCommande.Statut.choices).get(d["statut"], d["statut"]) for d in data]
    valeurs = [d["nb"] for d in data]
    return JsonResponse({
        "labels": labels,
        "valeurs": valeurs,
        "couleurs": ["#6c757d", "#0d6efd", "#0dcaf0", "#198754", "#dc3545"]
    })


@login_required
def api_graphique_magasin_occupation(request):
    """Occupation magasin par zone (Bar)."""
    zones = ZoneStockage.objects.annotate(
        nb_total=Count("rayons__emplacements"),
        nb_occupes=Count("rayons__emplacements", filter=Q(rayons__emplacements__statut="OCCUPE"))
    )
    labels = [z.code for z in zones]
    taux = [round((z.nb_occupes / z.nb_total * 100) if z.nb_total > 0 else 0, 1) for z in zones]
    return JsonResponse({
        "labels": labels,
        "valeurs": taux,
        "couleurs": [z.couleur for z in zones]
    })


@login_required
def api_kpis(request):
    """KPIs temps réel — rafraîchissement AJAX."""
    today = timezone.now().date()
    matieres = MatierePremiere.objects.filter(actif=True)
    pfs = ProduitFini.objects.filter(actif=True)
    nb_mp = matieres.count()
    nb_mp_rupt = matieres.filter(stock_actuel__lte=0).count()
    
    return JsonResponse({
        "mp_total": nb_mp,
        "mp_rupture": nb_mp_rupt,
        "mp_critique": matieres.filter(stock_actuel__gt=0, stock_actuel__lte=F("stock_minimum")).count(),
        "mp_alerte": matieres.filter(stock_actuel__gt=F("stock_minimum"), stock_actuel__lte=F("point_commande")).count(),
        "mp_valeur": float(matieres.aggregate(total=Sum(F("stock_actuel") * F("prix_unitaire")))["total"] or 0),
        "mp_dispo": round(((nb_mp - nb_mp_rupt) / nb_mp * 100) if nb_mp > 0 else 0, 1),
        
        "pf_total": pfs.count(),
        "pf_rupture": pfs.filter(stock_actuel__lte=0).count(),
        "pf_critique": pfs.filter(stock_actuel__gt=0, stock_actuel__lte=F("stock_minimum")).count(),
        "pf_valeur": float(pfs.aggregate(total=Sum(F("stock_actuel") * F("prix_unitaire")))["total"] or 0),
        
        "cmd_attente": BonCommande.objects.filter(statut=BonCommande.Statut.BROUILLON).count(),
        "cmd_retard": BonCommande.objects.exclude(statut__in=['RECU', 'ANNULE']).filter(date_reception_prevue__lt=today).count(),
        "prop_valider": PropositionCommande.objects.filter(statut=PropositionCommande.Statut.EN_ATTENTE).count(),
    })


# ============================================================
# RAPPORTS
# ============================================================

# --- Rapports Détaillés ---

class RapportIndexView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/rapports/index.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from django.db.models import Count, Q, F
        from django.utils import timezone
        import datetime
        
        today = timezone.now().date()
        un_mois_ago = today - datetime.timedelta(days=30)
        
        # 1. Stock
        ctx["cnt_ruptures"] = MatierePremiere.objects.filter(stock_actuel__lte=0, actif=True).count() + \
                              ProduitFini.objects.filter(stock_actuel__lte=0, actif=True).count()
        
        # 2. ABC
        ctx["cnt_abc"] = MatierePremiere.objects.exclude(Q(classe_abc__isnull=True) | Q(classe_abc="")).count()
        
        # 3. Mouvements (30j)
        ctx["cnt_mouvements"] = MouvementStock.objects.filter(date_mouvement__gte=un_mois_ago).count()
        
        # 4. Appro
        ctx["cnt_commandes"] = BonCommande.objects.filter(statut__in=["ENVOYE", "CONFIRME"]).count()
        
        # 5. Fournisseurs
        ctx["cnt_fournisseurs"] = Fournisseur.objects.filter(actif=True).count()
        
        # 6. MRP
        ctx["cnt_mrp"] = PropositionCommande.objects.filter(statut=PropositionCommande.Statut.EN_ATTENTE).count()
        
        # 7. Magasin
        total_empl = Emplacement.objects.count()
        occ_empl = Emplacement.objects.filter(statut="OCCUPE").count()
        ctx["pct_magasin"] = round((occ_empl / total_empl * 100), 1) if total_empl > 0 else 0
        
        # 8. Produits Finis
        ctx["cnt_pf"] = ProduitFini.objects.filter(actif=True).count()
        
        return ctx

class RapportStockView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/rapports/stock.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        matieres = MatierePremiere.objects.filter(actif=True)
        produits = ProduitFini.objects.filter(actif=True)
        
        ctx["valeur_mp"] = matieres.aggregate(t=Sum(F("stock_actuel") * F("prix_unitaire")))["t"] or 0
        ctx["valeur_pf"] = produits.aggregate(t=Sum(F("stock_actuel") * F("prix_unitaire")))["t"] or 0
        ctx["stock_statut"] = {
            "rupture": matieres.filter(stock_actuel__lte=0).count() + produits.filter(stock_actuel__lte=0).count(),
            "critique": matieres.filter(stock_actuel__gt=0, stock_actuel__lte=F("stock_minimum")).count() + produits.filter(stock_actuel__gt=0, stock_actuel__lte=F("stock_minimum")).count(),
            "normal": matieres.filter(stock_actuel__gt=F("stock_minimum")).count() + produits.filter(stock_actuel__gt=F("stock_minimum")).count(),
        }
        ctx["top_mp_critiques"] = matieres.filter(stock_actuel__lte=F("stock_minimum")).order_by("stock_actuel")[:10]
        ctx["top_pf_critiques"] = produits.filter(stock_actuel__lte=F("stock_minimum")).order_by("stock_actuel")[:10]
        
        # Données graphique valeur par catégorie
        cat_data = matieres.values("categorie").annotate(val=Sum(F("stock_actuel") * F("prix_unitaire"))).order_by("-val")
        ctx["cat_labels"] = [dict(MatierePremiere.Categorie.choices).get(d["categorie"], d["categorie"]) for d in cat_data]
        ctx["cat_values"] = [float(d["val"] or 0) for d in cat_data]
        
        return ctx

class RapportABCView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/rapports/abc.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        import json
        
        # 1. Récupération des matières actives
        matieres_qs = MatierePremiere.objects.filter(actif=True).select_related('unite')
        
        # 2. Calcul des valeurs de stock et tri
        matieres_list = []
        total_valeur = Decimal("0")
        
        for m in matieres_qs:
            # Calcul sécurisé (gestion du None)
            val = (m.stock_actuel or Decimal("0")) * (m.prix_unitaire or Decimal("0"))
            total_valeur += val
            matieres_list.append({
                'id': m.id,
                'reference': m.reference,
                'nom': m.nom,
                'stock_actuel': m.stock_actuel,
                'unite_symbole': m.unite.symbole if m.unite else "U",
                'valeur_stock': val,
                # On garde une référence à l'objet pour les liens éventuels
                'obj': m
            })
            
        # Tri par valeur de stock décroissante (essentiel pour ABC/Pareto)
        matieres_list.sort(key=lambda x: x['valeur_stock'], reverse=True)
        
        # 3. Calcul du cumulé et des classes A, B, C
        cumule_valeur = Decimal("0")
        abc_stats = {
            'A': {'nb': 0, 'val': Decimal("0")},
            'B': {'nb': 0, 'val': Decimal("0")},
            'C': {'nb': 0, 'val': Decimal("0")},
            'NC': {'nb': 0, 'val': Decimal("0")}
        }
        
        chart_labels = []
        chart_values = []
        chart_cumule = []
        
        for i, item in enumerate(matieres_list):
            val = item['valeur_stock']
            cumule_valeur += val
            
            # Calcul du pourcentage cumulé
            if total_valeur > 0:
                pct_cumule = float((cumule_valeur / total_valeur) * 100)
            else:
                pct_cumule = 0.0
                
            # Détermination de la classe (Loi de Pareto 80/15/5)
            if total_valeur == 0:
                classe = "NC"
            elif pct_cumule <= 80:
                classe = "A"
            elif pct_cumule <= 95:
                classe = "B"
            else:
                classe = "C"
                
            item['classe_abc'] = classe
            item['pct_cumule'] = pct_cumule
            
            # Mise à jour des stats globales
            abc_stats[classe]['nb'] += 1
            abc_stats[classe]['val'] += val
            
            # Préparation des données du graphique (Top 40 pour la lisibilité)
            if i < 40:
                chart_labels.append(item['reference'])
                chart_values.append(float(val))
                chart_cumule.append(round(pct_cumule, 1))

        ctx["matieres_abc"] = matieres_list
        ctx["abc_stats"] = abc_stats
        ctx["total_valeur"] = total_valeur
        
        # Données JSON pour Chart.js
        ctx["chart_data_json"] = json.dumps({
            "labels": chart_labels,
            "values": chart_values,
            "cumulative": chart_cumule
        })
        
        # Historique (conservé)
        ctx["historique_suffisant"] = MouvementStock.objects.filter(type_mouvement="SORTIE").count() > 10
        
        return ctx

class RapportMouvementsView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/rapports/mouvements.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        q = Q()
        
        start_date = self.request.GET.get("date_debut")
        end_date = self.request.GET.get("date_fin")
        type_mvt = self.request.GET.get("type_mouvement")
        user_id = self.request.GET.get("utilisateur")
        
        if start_date: q &= Q(date_mouvement__date__gte=start_date)
        if end_date: q &= Q(date_mouvement__date__lte=end_date)
        if type_mvt: q &= Q(type_mouvement=type_mvt)
        if user_id: q &= Q(operateur_id=user_id)
        
        mvts = MouvementStock.objects.filter(q).select_related("matiere", "produit_fini", "operateur")
        ctx["mouvements"] = mvts
        
        ctx["stats"] = mvts.values("type_mouvement").annotate(nb=Count("id"), qty=Sum("quantite"))
        
        # Tendance quotidienne (30 derniers jours par défaut)
        from django.db.models.functions import TruncDay
        tendance = (
            mvts.annotate(jour=TruncDay("date_mouvement"))
            .values("jour", "type_mouvement")
            .annotate(total=Sum("quantite"))
            .order_by("jour")
        )
        
        import json
        chart_data = {}
        for t in tendance:
            j = t['jour'].strftime('%d/%m')
            if j not in chart_data: chart_data[j] = {'ENTREE': 0, 'SORTIE': 0}
            chart_data[j][t['type_mouvement']] = float(t['total'])
            
        ctx["chart_labels_json"] = json.dumps(list(chart_data.keys()))
        ctx["chart_entrees_json"] = json.dumps([d['ENTREE'] for d in chart_data.values()])
        ctx["chart_sorties_json"] = json.dumps([d['SORTIE'] for d in chart_data.values()])
        
        return ctx

class RapportApproView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/rapports/approvisionnement.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = timezone.now().date()
        
        ctx["commandes_ouvertes"] = BonCommande.objects.filter(statut__in=["ENVOYE", "CONFIRME"])
        ctx["commandes_retard"] = BonCommande.objects.exclude(statut__in=["RECU", "ANNULE"]).filter(date_reception_prevue__lt=today)
        ctx["propositions"] = PropositionCommande.objects.filter(statut=PropositionCommande.Statut.EN_ATTENTE)
        ctx["sous_rop"] = MatierePremiere.objects.filter(stock_actuel__lte=F("point_commande"), actif=True)
        ctx["montant_engage"] = ctx["commandes_ouvertes"].aggregate(t=Sum("montant_total"))["t"] or 0
        
        return ctx

class RapportFournisseursView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/rapports/fournisseurs.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        fournisseurs = Fournisseur.objects.annotate(
            nb_cmd=Count("bons_commande"),
            val_cmd=Sum("bons_commande__montant_total"),
            nb_retards=Count("bons_commande", filter=Q(bons_commande__date_reception_prevue__lt=timezone.now().date(), bons_commande__statut__in=["ENVOYE", "CONFIRME"]))
        ).order_by("-val_cmd")
        
        ctx["fournisseurs"] = fournisseurs
        ctx["fournisseurs_actifs"] = fournisseurs.filter(actif=True).count()
        ctx["fournisseurs_surveiller"] = fournisseurs.filter(statut="A_SURVEILLER").count()
        
        return ctx

class RapportMRPView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/rapports/mrp.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from produits.models import Nomenclature
        from approvisionnement.models import PlanMRP
        ctx["nomenclatures"] = Nomenclature.objects.select_related("produit_fini").prefetch_related("lignes__matiere")
        ctx["besoins"] = PlanMRP.objects.filter(statut="CALCULE").select_related("matiere")
        
        # Blocants: Matières en rupture nécessaires pour des PF
        ctx["bloquants"] = MatierePremiere.objects.filter(
            stock_actuel__lte=0,
            utilise_dans__isnull=False
        ).distinct()
        
        return ctx

class RapportMagasinView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/rapports/magasin.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        emplacements = Emplacement.objects.all()
        ctx["total"] = emplacements.count()
        ctx["libres"] = emplacements.filter(statut="LIBRE").count()
        ctx["occupes"] = emplacements.filter(statut="OCCUPE").count()
        ctx["bloques"] = emplacements.filter(statut="BLOQUE").count()
        
        zones = ZoneStockage.objects.annotate(
            nb_total=Count("rayons__emplacements"),
            nb_occ=Count("rayons__emplacements", filter=Q(rayons__emplacements__statut="OCCUPE"))
        )
        ctx["zones"] = zones
        
        import json
        ctx["zone_labels_json"] = json.dumps([z.nom for z in zones])
        ctx["zone_pct_json"] = json.dumps([
            round((z.nb_occ / z.nb_total * 100), 1) if z.nb_total > 0 else 0 
            for z in zones
        ])
        
        return ctx

class RapportProduitsFinisView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/rapports/produits_finis.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        pfs = ProduitFini.objects.filter(actif=True)
        ctx["total_nb"] = pfs.count()
        ctx["valeur_totale"] = pfs.aggregate(t=Sum(F("stock_actuel") * F("prix_unitaire")))["t"] or 0
        ctx["ruptures"] = pfs.filter(stock_actuel__lte=0).count()
        ctx["critiques"] = pfs.filter(stock_actuel__gt=0, stock_actuel__lte=F("stock_minimum")).count()
        
        ctx["pfs_par_categorie"] = pfs.values("categorie").annotate(nb=Count("id"), val=Sum(F("stock_actuel") * F("prix_unitaire")))
        
        return ctx

# ============================================================
# EXPORT GÉNÉRIQUE
# ============================================================

@login_required
def exporter_rapport(request, type_rapport, format_file):
    """
    Exporteur de rapports en CSV ou PDF.
    type_rapport: stock, abc, mouvements, appro, fournisseurs, mrp, magasin, pf
    format_file: csv, pdf
    """
    import csv
    from django.http import HttpResponse
    from django.utils import timezone
    
    filename = f"rapport_{type_rapport}_{timezone.now().strftime('%Y%m%d_%H%M')}"
    
    if format_file == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{filename}.csv"'
        writer = csv.writer(response)
        
        if type_rapport == "stock":
            writer.writerow(["Référence", "Nom", "Stock Actuel", "Unité", "Valeur (DH)"])
            for m in MatierePremiere.objects.filter(actif=True):
                writer.writerow([m.reference, m.nom, m.stock_actuel, m.unite.symbole, m.stock_actuel * m.prix_unitaire])
            for p in ProduitFini.objects.filter(actif=True):
                writer.writerow([p.reference, p.nom, p.stock_actuel, p.unite.symbole, p.stock_actuel * p.prix_unitaire])
        
        elif type_rapport == "mouvements":
            writer.writerow(["Date", "Type", "Article", "Quantité", "Opérateur"])
            for m in MouvementStock.objects.all().select_related("matiere", "produit_fini", "operateur"):
                article = m.matiere.nom if m.matiere else m.produit_fini.nom
                writer.writerow([m.date_mouvement, m.type_mouvement, article, m.quantite, m.operateur.username])
        
        # ... autres types de rapports CSV ici ...
        else:
            writer.writerow(["Rapport non encore implémenté en CSV"])
            
        return response

    elif format_file == "pdf":
        # Réutilisation de la logique reportlab existante (simplifiée pour l'exemple)
        return generer_rapport_stock(request) # Fallback sur le rapport existant pour l'instant

    return HttpResponse("Format non supporté", status=400)


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

@login_required
def api_notifications(request):
    """
    API retournant les notifications dynamiques (alertes temps réel) 
    et les notifications persistantes de la base de données.
    """
    from django.db.models import F
    from django.urls import reverse
    
    today = timezone.now().date()
    notifs = []
    
    # 1. Matières Premières en rupture
    mps_rupture = MatierePremiere.objects.filter(stock_actuel__lte=0, actif=True)
    for mp in mps_rupture:
        notifs.append({
            'type': 'stock',
            'level': 'danger',
            'title': _("Matière en rupture"),
            'message': _(f"La matière {mp.nom} ({mp.reference}) est en rupture de stock."),
            'url': reverse('produits:matiere-detail', args=[mp.pk]),
            'created_at': mp.date_modification.isoformat()
        })
        
    # 2. Matières Premières critiques
    mps_critiques = MatierePremiere.objects.filter(stock_actuel__gt=0, stock_actuel__lte=F('stock_minimum'), actif=True)
    for mp in mps_critiques:
        notifs.append({
            'type': 'stock',
            'level': 'warning',
            'title': _("Stock critique"),
            'message': _(f"Le stock de {mp.nom} est sous le seuil minimum."),
            'url': reverse('produits:matiere-detail', args=[mp.pk]),
            'created_at': mp.date_modification.isoformat()
        })
        
    # 3. Produits Finis en rupture
    pfs_rupture = ProduitFini.objects.filter(stock_actuel__lte=0, actif=True)
    for pf in pfs_rupture:
        notifs.append({
            'type': 'stock',
            'level': 'danger',
            'title': _("Produit fini en rupture"),
            'message': _(f"Le produit {pf.nom} ({pf.reference}) est épuisé."),
            'url': reverse('produits:produit-fini-detail', args=[pf.pk]),
            'created_at': pf.date_modification.isoformat()
        })

    # 4. Commandes en retard
    commandes_retard = BonCommande.objects.filter(statut__in=['ENVOYE', 'CONFIRME'], date_reception_prevue__lt=today)
    for bc in commandes_retard:
        notifs.append({
            'type': 'appro',
            'level': 'danger',
            'title': _("Retard de livraison"),
            'message': _(f"La commande {bc.reference} de {bc.fournisseur.nom} est en retard."),
            'url': reverse('approvisionnement:commande-detail', args=[bc.pk]),
            'created_at': bc.date_creation.isoformat()
        })

    # 5. Propositions MRP à valider
    propos = PropositionCommande.objects.filter(statut=PropositionCommande.Statut.EN_ATTENTE)
    if propos.exists():
        notifs.append({
            'type': 'appro',
            'level': 'info',
            'title': _("Nouvelles propositions MRP"),
            'message': _(f"{propos.count()} propositions d'approvisionnement sont en attente de validation."),
            'url': reverse('approvisionnement:commandes-a-valider'),
            'created_at': timezone.now().isoformat()
        })

    # 6. Emplacements bloqués
    empl_bloques = Emplacement.objects.filter(statut='BLOQUE')
    for em in empl_bloques:
         notifs.append({
            'type': 'magasin',
            'level': 'warning',
            'title': _("Emplacement bloqué"),
            'message': _(f"L'emplacement {em.code} est bloqué."),
            'url': reverse('magasin:plan'),
            'created_at': timezone.now().isoformat()
        })

    # 7. Notifications persistantes (base de données)
    db_notifs = request.user.notifications.filter(lue=False).order_by('-date_envoi')[:10]
    for n in db_notifs:
        notifs.append({
            'type': 'système',
            'level': 'primary' if n.priorite == 'HAUTE' else 'secondary',
            'title': n.titre,
            'message': n.message,
            'url': n.lien or '#',
            'created_at': n.date_envoi.isoformat()
        })

    # 8. Tri par date décroissante
    notifs.sort(key=lambda x: x['created_at'], reverse=True)

    return JsonResponse({
        'count': len(notifs),
        'notifications': notifs[:3]  # Limiter à 3 pour le dropdown
    })

class AlertesView(LoginRequiredMixin, TemplateView):
    """
    Vue listant toutes les alertes du système.
    Agit comme un hub central pour les urgences.
    """
    template_name = "dashboard/alertes.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from django.db.models import F
        from django.urls import reverse
        from django.utils import timezone
        
        today = timezone.now().date()
        alertes = []
        
        # 1. Ruptures de stock (MP & PF)
        mps_rupture = MatierePremiere.objects.filter(stock_actuel__lte=0, actif=True)
        for mp in mps_rupture:
            alertes.append({
                'type': 'Rupture',
                'level': 'danger',
                'title': _("Matière en rupture"),
                'message': _(f"La matière {mp.nom} ({mp.reference}) est en rupture totale."),
                'url': reverse('produits:matiere-detail', args=[mp.pk]),
                'date': mp.date_modification,
                'category': 'stock'
            })
            
        pfs_rupture = ProduitFini.objects.filter(stock_actuel__lte=0, actif=True)
        for pf in pfs_rupture:
            alertes.append({
                'type': 'Rupture',
                'level': 'danger',
                'title': _("Produit fini en rupture"),
                'message': _(f"Le produit {pf.nom} ({pf.reference}) est en rupture totale."),
                'url': reverse('produits:produit-fini-detail', args=[pf.pk]),
                'date': pf.date_modification,
                'category': 'stock'
            })
            
        # 2. Stocks Critiques (Sous seuil min)
        mps_critiques = MatierePremiere.objects.filter(stock_actuel__gt=0, stock_actuel__lte=F('stock_minimum'), actif=True)
        for mp in mps_critiques:
            alertes.append({
                'type': 'Critique',
                'level': 'warning',
                'title': _("Stock critique (MP)"),
                'message': _(f"Le stock de {mp.nom} ({mp.stock_actuel} {mp.unite.symbole if mp.unite else ''}) est sous le seuil minimum ({mp.stock_minimum})."),
                'url': reverse('produits:matiere-detail', args=[mp.pk]),
                'date': mp.date_modification,
                'category': 'stock'
            })
            
        pfs_critiques = ProduitFini.objects.filter(stock_actuel__gt=0, stock_actuel__lte=F('stock_minimum'), actif=True)
        for pf in pfs_critiques:
            alertes.append({
                'type': 'Critique',
                'level': 'warning',
                'title': _("Stock critique (PF)"),
                'message': _(f"Le stock de {pf.nom} ({pf.stock_actuel} {pf.unite.symbole if pf.unite else ''}) est sous le seuil minimum ({pf.stock_minimum})."),
                'url': reverse('produits:produit-fini-detail', args=[pf.pk]),
                'date': pf.date_modification,
                'category': 'stock'
            })
            
        # 3. Retards de livraison
        commandes_retard = BonCommande.objects.filter(statut__in=['ENVOYE', 'CONFIRME'], date_reception_prevue__lt=today)
        for bc in commandes_retard:
            alertes.append({
                'type': 'Commande',
                'level': 'danger',
                'title': _("Livraison en retard"),
                'message': _(f"Le bon de commande {bc.reference} ({bc.fournisseur.nom}) était attendu le {bc.date_reception_prevue:%d/%m/%Y}."),
                'url': reverse('approvisionnement:commande-detail', args=[bc.pk]),
                'date': bc.date_creation,
                'category': 'appro'
            })
            
        # 4. Propositions MRP en attente
        propos = PropositionCommande.objects.filter(statut=PropositionCommande.Statut.EN_ATTENTE)
        if propos.exists():
            alertes.append({
                'type': 'Approvisionnement',
                'level': 'info',
                'title': _("Propositions à valider"),
                'message': _(f"{propos.count()} propositions d'approvisionnement sont en attente de validation."),
                'url': reverse('approvisionnement:commandes-a-valider'),
                'date': timezone.now(),
                'category': 'appro'
            })
            
        # 5. Magasin (Emplacements bloqués)
        empl_bloques = Emplacement.objects.filter(statut='BLOQUE')
        for em in empl_bloques:
             alertes.append({
                'type': 'Magasin',
                'level': 'warning',
                'title': _("Emplacement bloqué"),
                'message': _(f"L'emplacement {em.code} est actuellement bloqué pour maintenance ou autre raison."),
                'url': reverse('magasin:plan'),
                'date': timezone.now(),
                'category': 'magasin'
            })

        # Tri par gravité (danger > warning > info)
        gravity = {'danger': 0, 'warning': 1, 'info': 2}
        alertes.sort(key=lambda x: gravity.get(x['level'], 99))
        
        ctx['alertes'] = alertes
        ctx['total_alertes'] = len(alertes)
        return ctx
