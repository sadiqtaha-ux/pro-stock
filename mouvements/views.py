"""
mouvements/views.py
Personne 2 — Backend Stocks
Entrées/Sorties, État du stock, Alertes, Export CSV, API JSON
"""
import csv
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, CreateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q, Sum, F
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.shortcuts import render

from core.mixins import KanbanListMixin, ExportMixin
from core.models import JournalActivite
from core.utils import log_action
from .models import MouvementStock
from produits.models import MatierePremiere, ProduitFini
from produits.views import UnitValidationMixin


# ─────────────────────────────────────────────
# 1. LISTE COMPLÈTE DES MOUVEMENTS
# ─────────────────────────────────────────────
class MouvementListeView(LoginRequiredMixin, KanbanListMixin, ExportMixin, ListView):
    model               = MouvementStock
    template_name       = "mouvements/liste.html"
    kanban_template_name = "mouvements/kanban.html"
    context_object_name = "mouvements"
    paginate_by         = 30
    export_fields       = ['date_mouvement', 'type_mouvement', 'type_stock', 'nom_article', 'quantite', 'operateur__username']
    export_headers      = ['Date', 'Type Mvt', 'Type Stock', 'Article', 'Quantité', 'Opérateur']

    def _get_export_data(self, queryset):
        """Surcharge pour gérer l'affichage de l'article (Matière ou Produit Fini)."""
        rows = []
        for obj in queryset:
            article = obj.matiere.nom if obj.type_stock == 'MATIERE' and obj.matiere else ""
            if not article and obj.produit_fini:
                article = obj.produit_fini.nom
                
            rows.append([
                obj.date_mouvement.strftime('%d/%m/%Y %H:%M'),
                obj.get_type_mouvement_display(),
                dict(MouvementStock.TYPE_STOCK_CHOICES).get(obj.type_stock, obj.type_stock),
                article,
                obj.quantite,
                obj.operateur.username if obj.operateur else "-"
            ])
        return rows

    def get_queryset(self):
        qs = MouvementStock.objects.select_related(
            "matiere", "produit_fini", "operateur", "bon_commande", "matiere__unite", "produit_fini__unite"
        )
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(
                Q(matiere__nom__icontains=q) |
                Q(matiere__reference__icontains=q) |
                Q(produit_fini__nom__icontains=q) |
                Q(produit_fini__reference__icontains=q) |
                Q(numero_lot__icontains=q)
            )
        
        type_stock = self.request.GET.get("type_stock")
        if type_stock:
            qs = qs.filter(type_stock=type_stock)

        type_mvt = self.request.GET.get("type")
        if type_mvt:
            qs = qs.filter(type_mouvement=type_mvt)

        date_debut = self.request.GET.get("date_debut")
        if date_debut:
            qs = qs.filter(date_mouvement__date__gte=date_debut)

        date_fin = self.request.GET.get("date_fin")
        if date_fin:
            qs = qs.filter(date_mouvement__date__lte=date_fin)
            
        operateur = self.request.GET.get("operateur")
        if operateur:
            qs = qs.filter(operateur_id=operateur)

        return qs.order_by("-date_mouvement")

    def get(self, request, *args, **kwargs):
        export_type = request.GET.get('export')
        if export_type == 'csv':
            return self.render_to_csv(self.get_queryset(), filename_prefix="mouvements")
        elif export_type == 'pdf':
            return self.render_to_pdf(self.get_queryset(), title="Journal des Mouvements de Stock", filename_prefix="mouvements")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["types_mvt"] = MouvementStock.TypeMouvement.choices
        ctx["types_stock"] = MouvementStock.TYPE_STOCK_CHOICES
        
        # Calcul des KPIs sur le queryset filtré
        qs = self.get_queryset()
        ctx["movements_count"] = qs.count()
        ctx["entree_count"] = qs.filter(type_mouvement=MouvementStock.TypeMouvement.ENTREE).count()
        ctx["sortie_count"] = qs.filter(type_mouvement=MouvementStock.TypeMouvement.SORTIE).count()
        ctx["ajustement_count"] = qs.filter(type_mouvement=MouvementStock.TypeMouvement.AJUSTEMENT).count()

        from django.contrib.auth import get_user_model
        ctx["operateurs"] = get_user_model().objects.all()
        return ctx


# ─────────────────────────────────────────────
# 2. CRÉER UN MOUVEMENT (ENTRÉE, SORTIE, AJUSTEMENT)
# ─────────────────────────────────────────────
class MouvementCreerView(LoginRequiredMixin, UnitValidationMixin, CreateView):
    model         = MouvementStock
    template_name = "mouvements/form.html"
    from .forms import MouvementStockForm
    form_class    = MouvementStockForm

    success_url = reverse_lazy("mouvements:liste")

    def get_initial(self):
        initial = super().get_initial()
        type_mvt = self.request.GET.get('type')
        if type_mvt in dict(MouvementStock.TypeMouvement.choices):
            initial['type_mouvement'] = type_mvt
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        import json
        
        # Mapping Stock
        matieres_stock = {m.id: float(m.stock_actuel) for m in MouvementStock.matiere.field.related_model.objects.all()}
        produits_stock = {p.id: float(p.stock_actuel) for p in MouvementStock.produit_fini.field.related_model.objects.all()}
        
        context['matieres_stock_json'] = json.dumps(matieres_stock)
        context['produits_stock_json'] = json.dumps(produits_stock)
        
        return context

    def form_valid(self, form):
        form.instance.operateur = self.request.user
        response = super().form_valid(form)
        
        article = self.object.matiere or self.object.produit_fini
        log_action(
            self.request,
            JournalActivite.TypeAction.CREATION,
            'MouvementStock',
            self.object.pk,
            f"Mouvement de stock ({self.object.get_type_mouvement_display()}) pour {article}"
        )
        
        messages.success(self.request, "Mouvement enregistré avec succès.")
        return response

    def form_invalid(self, form):
        messages.error(self.request, "Erreur dans le formulaire. Vérifiez les champs.")
        return super().form_invalid(form)





# ─────────────────────────────────────────────
# 5. ÉTAT DU STOCK (tableau de bord)
# ─────────────────────────────────────────────
class EtatStockView(LoginRequiredMixin, ExportMixin, ListView):
    """
    Affiche l'état actuel du stock pour chaque matière première.
    Calcule les alertes (stock <= seuil minimum).
    Supporte l'export CSV et PDF via ExportMixin.
    """
    model = MatierePremiere
    template_name = "mouvements/etat_stock.html"
    context_object_name = "matieres_list"
    export_fields = ['reference', 'nom', 'stock_recalc', 'unite__symbole', 'stock_minimum', 'stock_maximum', 'valeur_recalc']
    export_headers = ['Référence', 'Désignation', 'Stock Actuel', 'Unité', 'Stock Min', 'Stock Max', 'Valeur (DH)']

    def get_queryset(self):
        from django.db.models.functions import Coalesce
        from decimal import Decimal
        qs = MatierePremiere.objects.filter(actif=True).select_related('unite').annotate(
            calc_entrees=Coalesce(Sum('mouvements__quantite', filter=Q(mouvements__type_mouvement='ENTREE')), Decimal('0')),
            calc_sorties=Coalesce(Sum('mouvements__quantite', filter=Q(mouvements__type_mouvement='SORTIE')), Decimal('0')),
            stock_recalc=F('calc_entrees') - F('calc_sorties'),
            valeur_recalc=F('stock_recalc') * F('prix_unitaire')
        )
        
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(Q(nom__icontains=q) | Q(reference__icontains=q))
            
        return qs.order_by('nom')

    def get(self, request, *args, **kwargs):
        export_type = request.GET.get('export')
        if export_type == 'csv':
            return self.render_to_csv(self.get_queryset(), filename_prefix="etat_stock")
        elif export_type == 'pdf':
            return self.render_to_pdf(self.get_queryset(), title="État du Stock de Matières Premières", filename_prefix="etat_stock")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        matieres = self.get_queryset()
        
        stock_data = []
        alertes = []
        
        for m in matieres:
            stock_actuel = m.stock_recalc
            
            # Pourcentage du stock max
            pourcentage = 0
            if m.stock_maximum and m.stock_maximum > 0:
                pourcentage = round((float(stock_actuel) / float(m.stock_maximum)) * 100, 1)

            # Statut de l'alerte
            statut = "ok"
            if stock_actuel <= 0:
                statut = "rupture"
                alertes.append({"matiere": m, "stock": stock_actuel, "niveau": "rupture"})
            elif stock_actuel <= m.stock_minimum:
                statut = "critique"
                alertes.append({"matiere": m, "stock": stock_actuel, "niveau": "critique"})

            stock_data.append({
                "matiere": m,
                "stock_actuel": stock_actuel,
                "pourcentage": pourcentage,
                "statut": statut,
            })

        ctx.update({
            "stock_data": stock_data,
            "alertes": alertes,
            "nb_alertes": len(alertes),
            "date": timezone.now(),
        })
        return ctx


# ─────────────────────────────────────────────
# 6. EXPORT CSV DE L'HISTORIQUE
# ─────────────────────────────────────────────


# ─────────────────────────────────────────────
# 7. API JSON — ÉTAT DU STOCK (pour P4 dashboard)
# ─────────────────────────────────────────────
@login_required
def api_etat_stock(request):
    """
    Endpoint JSON pour alimenter les graphiques du dashboard (Personne 4).
    URL: /mouvements/api/etat/
    """
    matieres = MatierePremiere.objects.all().order_by("nom")
    data = []

    for matiere in matieres:
        entrees = MouvementStock.objects.filter(
            matiere=matiere,
            type_mouvement=MouvementStock.TypeMouvement.ENTREE
        ).aggregate(total=Sum("quantite"))["total"] or 0

        sorties = MouvementStock.objects.filter(
            matiere=matiere,
            type_mouvement=MouvementStock.TypeMouvement.SORTIE
        ).aggregate(total=Sum("quantite"))["total"] or 0

        stock_actuel = float(entrees - sorties)

        data.append({
            "id": matiere.id,
            "nom": matiere.nom,
            "reference": matiere.reference,
            "unite": str(matiere.unite) if hasattr(matiere, 'unite') else "",
            "stock_actuel": stock_actuel,
            "stock_min": float(matiere.stock_min) if hasattr(matiere, 'stock_min') and matiere.stock_min else 0,
            "stock_max": float(matiere.stock_max) if hasattr(matiere, 'stock_max') and matiere.stock_max else 0,
            "alerte": stock_actuel <= float(matiere.stock_min) if hasattr(matiere, 'stock_min') and matiere.stock_min else False,
        })

    return JsonResponse({"status": "ok", "stock": data}, safe=False)
