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
from .models import MouvementStock
from produits.models import MatierePremiere


# ─────────────────────────────────────────────
# 1. LISTE COMPLÈTE DES MOUVEMENTS
# ─────────────────────────────────────────────
class MouvementListeView(LoginRequiredMixin, ListView):
    model               = MouvementStock
    template_name       = "mouvements/liste.html"
    context_object_name = "mouvements"
    paginate_by         = 30

    def get_queryset(self):
        qs = MouvementStock.objects.select_related(
            "matiere", "operateur", "bon_commande"
        )
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(
                Q(matiere__nom__icontains=q) |
                Q(matiere__reference__icontains=q) |
                Q(numero_lot__icontains=q)
            )
        type_mvt = self.request.GET.get("type")
        if type_mvt:
            qs = qs.filter(type_mouvement=type_mvt)

        date_debut = self.request.GET.get("date_debut")
        if date_debut:
            qs = qs.filter(date_mouvement__date__gte=date_debut)

        date_fin = self.request.GET.get("date_fin")
        if date_fin:
            qs = qs.filter(date_mouvement__date__lte=date_fin)

        return qs.order_by("-date_mouvement")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["types"] = MouvementStock.TypeMouvement.choices
        return ctx


# ─────────────────────────────────────────────
# 2. CRÉER UN MOUVEMENT (ENTRÉE OU SORTIE)
# ─────────────────────────────────────────────
class MouvementCreerView(LoginRequiredMixin, CreateView):
    model         = MouvementStock
    template_name = "mouvements/form.html"
    fields        = [
        "matiere", "type_mouvement", "quantite", "quantite_avant",
        "motif", "numero_lot", "date_peremption", "bon_commande"
    ]
    success_url = reverse_lazy("mouvements:liste")

    def form_valid(self, form):
        form.instance.operateur = self.request.user
        messages.success(self.request, "Mouvement enregistré avec succès.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Erreur dans le formulaire. Vérifiez les champs.")
        return super().form_invalid(form)


# ─────────────────────────────────────────────
# 3. LISTE DES ENTRÉES
# ─────────────────────────────────────────────
class EntreeListeView(LoginRequiredMixin, ListView):
    model               = MouvementStock
    template_name       = "mouvements/entrees/liste.html"
    context_object_name = "mouvements"
    paginate_by         = 30

    def get_queryset(self):
        return MouvementStock.objects.filter(
            type_mouvement=MouvementStock.TypeMouvement.ENTREE
        ).select_related("matiere", "operateur").order_by("-date_mouvement")


# ─────────────────────────────────────────────
# 4. LISTE DES SORTIES
# ─────────────────────────────────────────────
class SortieListeView(LoginRequiredMixin, ListView):
    model               = MouvementStock
    template_name       = "mouvements/sorties/liste.html"
    context_object_name = "mouvements"
    paginate_by         = 30

    def get_queryset(self):
        return MouvementStock.objects.filter(
            type_mouvement=MouvementStock.TypeMouvement.SORTIE
        ).select_related("matiere", "operateur").order_by("-date_mouvement")


# ─────────────────────────────────────────────
# 5. ÉTAT DU STOCK (tableau de bord)
# ─────────────────────────────────────────────
@login_required
def etat_stock_view(request):
    """
    Affiche l'état actuel du stock pour chaque matière première.
    Calcule les alertes (stock <= seuil minimum).
    """
    matieres = MatierePremiere.objects.all().order_by("nom")

    stock_data = []
    alertes = []

    for matiere in matieres:
        # Calcul du stock actuel via les mouvements
        entrees = MouvementStock.objects.filter(
            matiere=matiere,
            type_mouvement=MouvementStock.TypeMouvement.ENTREE
        ).aggregate(total=Sum("quantite"))["total"] or 0

        sorties = MouvementStock.objects.filter(
            matiere=matiere,
            type_mouvement=MouvementStock.TypeMouvement.SORTIE
        ).aggregate(total=Sum("quantite"))["total"] or 0

        stock_actuel = entrees - sorties

        # Pourcentage du stock max
        pourcentage = 0
        if hasattr(matiere, 'stock_max') and matiere.stock_max and matiere.stock_max > 0:
            pourcentage = round((stock_actuel / matiere.stock_max) * 100, 1)

        # Statut de l'alerte
        statut = "ok"
        if hasattr(matiere, 'stock_min') and matiere.stock_min:
            if stock_actuel <= 0:
                statut = "rupture"
                alertes.append({"matiere": matiere, "stock": stock_actuel, "niveau": "rupture"})
            elif stock_actuel <= matiere.stock_min:
                statut = "critique"
                alertes.append({"matiere": matiere, "stock": stock_actuel, "niveau": "critique"})

        stock_data.append({
            "matiere": matiere,
            "stock_actuel": stock_actuel,
            "pourcentage": pourcentage,
            "statut": statut,
        })

    context = {
        "stock_data": stock_data,
        "alertes": alertes,
        "nb_alertes": len(alertes),
        "date": timezone.now(),
    }
    return render(request, "mouvements/etat_stock.html", context)


# ─────────────────────────────────────────────
# 6. EXPORT CSV DE L'HISTORIQUE
# ─────────────────────────────────────────────
@login_required
def export_csv_view(request):
    """
    Exporte tous les mouvements filtrés en fichier CSV téléchargeable.
    """
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="mouvements_stock.csv"'
    response.write('\ufeff')  # BOM pour Excel

    writer = csv.writer(response, delimiter=";")
    writer.writerow([
        "Date", "Matière première", "Référence", "Type",
        "Quantité", "Stock avant", "Stock après",
        "Numéro lot", "Date péremption", "Motif", "Opérateur"
    ])

    qs = MouvementStock.objects.select_related(
        "matiere", "operateur"
    ).order_by("-date_mouvement")

    # Appliquer les mêmes filtres que la liste
    q = request.GET.get("q")
    if q:
        qs = qs.filter(
            Q(matiere__nom__icontains=q) |
            Q(matiere__reference__icontains=q)
        )
    type_mvt = request.GET.get("type")
    if type_mvt:
        qs = qs.filter(type_mouvement=type_mvt)

    date_debut = request.GET.get("date_debut")
    if date_debut:
        qs = qs.filter(date_mouvement__date__gte=date_debut)

    date_fin = request.GET.get("date_fin")
    if date_fin:
        qs = qs.filter(date_mouvement__date__lte=date_fin)

    for mvt in qs:
        writer.writerow([
            mvt.date_mouvement.strftime("%d/%m/%Y %H:%M"),
            mvt.matiere.nom,
            mvt.matiere.reference,
            mvt.get_type_mouvement_display(),
            mvt.quantite,
            mvt.quantite_avant,
            mvt.quantite_apres,
            mvt.numero_lot or "",
            mvt.date_peremption.strftime("%d/%m/%Y") if mvt.date_peremption else "",
            mvt.motif or "",
            mvt.operateur.get_full_name() if mvt.operateur else "",
        ])

    return response


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
