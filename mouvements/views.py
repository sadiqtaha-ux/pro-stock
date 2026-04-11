"""
App Mouvements - Vues
Gestion des entrées, sorties, inventaires et historique
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView
from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Sum, F, Count
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from .models import MouvementStock, BonEntree, BonSortie, Inventaire, LigneInventaire
from .forms import (
    MouvementStockForm, BonEntreeForm, BonSortieForm,
    InventaireForm, LigneInventaireForm
)


# ============================================================
# HISTORIQUE MOUVEMENTS
# ============================================================

class HistoriqueMouvementsView(LoginRequiredMixin, ListView):
    """Historique complet des mouvements de stock."""
    model = MouvementStock
    template_name = 'mouvements/historique/liste.html'
    context_object_name = 'mouvements'
    paginate_by = 30

    def get_queryset(self):
        qs = MouvementStock.objects.select_related(
            'produit', 'lot', 'fournisseur', 'cree_par', 'valide_par'
        ).filter(statut=MouvementStock.StatutMouvement.VALIDE)

        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(
                Q(numero__icontains=q) |
                Q(produit__code__icontains=q) |
                Q(produit__designation__icontains=q) |
                Q(reference_document__icontains=q)
            )
        type_mvt = self.request.GET.get('type')
        if type_mvt:
            qs = qs.filter(type_mouvement=type_mvt)

        date_debut = self.request.GET.get('date_debut')
        if date_debut:
            qs = qs.filter(date_mouvement__date__gte=date_debut)

        date_fin = self.request.GET.get('date_fin')
        if date_fin:
            qs = qs.filter(date_mouvement__date__lte=date_fin)

        return qs.order_by('-date_mouvement')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['types_mouvement'] = MouvementStock.TypeMouvement.choices
        return context


# ============================================================
# ENTRÉES
# ============================================================

class BonEntreeListeView(LoginRequiredMixin, ListView):
    """Liste des bons d'entrée."""
    model = BonEntree
    template_name = 'mouvements/entree/liste.html'
    context_object_name = 'bons_entree'
    paginate_by = 25

    def get_queryset(self):
        qs = BonEntree.objects.select_related('fournisseur', 'cree_par')
        statut = self.request.GET.get('statut')
        if statut:
            qs = qs.filter(statut=statut)
        return qs.order_by('-date_reception')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['statuts'] = BonEntree.Statut.choices
        return context


class BonEntreeDetailView(LoginRequiredMixin, DetailView):
    model = BonEntree
    template_name = 'mouvements/entree/detail.html'
    context_object_name = 'bon_entree'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['lignes'] = self.object.mouvements.filter(
            type_mouvement=MouvementStock.TypeMouvement.ENTREE
        )
        return context


class BonEntreeCreerView(LoginRequiredMixin, CreateView):
    model = BonEntree
    form_class = BonEntreeForm
    template_name = 'mouvements/entree/form.html'
    success_url = reverse_lazy('mouvements:entree-liste')

    def form_valid(self, form):
        form.instance.cree_par = self.request.user
        messages.success(self.request, _("Bon d'entrée créé avec succès."))
        return super().form_valid(form)


@login_required
def valider_bon_entree(request, pk):
    """Valider un bon d'entrée et mettre à jour les stocks."""
    bon = get_object_or_404(BonEntree, pk=pk)
    if request.method == 'POST':
        if bon.statut in [BonEntree.Statut.BROUILLON, BonEntree.Statut.RECEPTION_PARTIELLE]:
            bon.statut = BonEntree.Statut.VALIDE
            bon.valide_par = request.user
            bon.date_validation = timezone.now()
            bon.save()
            messages.success(request, _("Bon d'entrée validé avec succès."))
        else:
            messages.error(request, _("Ce bon d'entrée ne peut pas être validé."))
    return redirect('mouvements:entree-detail', pk=pk)


# ============================================================
# SORTIES
# ============================================================

class BonSortieListeView(LoginRequiredMixin, ListView):
    model = BonSortie
    template_name = 'mouvements/sortie/liste.html'
    context_object_name = 'bons_sortie'
    paginate_by = 25

    def get_queryset(self):
        qs = BonSortie.objects.select_related('demandeur', 'cree_par')
        statut = self.request.GET.get('statut')
        if statut:
            qs = qs.filter(statut=statut)
        return qs.order_by('-date_demande')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['statuts'] = BonSortie.Statut.choices
        context['en_attente'] = BonSortie.objects.filter(statut=BonSortie.Statut.EN_ATTENTE).count()
        return context


class BonSortieDetailView(LoginRequiredMixin, DetailView):
    model = BonSortie
    template_name = 'mouvements/sortie/detail.html'
    context_object_name = 'bon_sortie'


class BonSortieCreerView(LoginRequiredMixin, CreateView):
    model = BonSortie
    form_class = BonSortieForm
    template_name = 'mouvements/sortie/form.html'
    success_url = reverse_lazy('mouvements:sortie-liste')

    def form_valid(self, form):
        form.instance.cree_par = self.request.user
        form.instance.demandeur = self.request.user
        messages.success(self.request, _("Bon de sortie créé avec succès."))
        return super().form_valid(form)


@login_required
def valider_bon_sortie(request, pk):
    """Valider un bon de sortie."""
    bon = get_object_or_404(BonSortie, pk=pk)
    if request.method == 'POST' and request.user.peut_valider:
        bon.statut = BonSortie.Statut.VALIDE
        bon.valide_par = request.user
        bon.date_validation = timezone.now()
        bon.save()
        messages.success(request, _("Bon de sortie validé."))
    return redirect('mouvements:sortie-detail', pk=pk)


# ============================================================
# INVENTAIRE
# ============================================================

class InventaireListeView(LoginRequiredMixin, ListView):
    model = Inventaire
    template_name = 'mouvements/inventaire/liste.html'
    context_object_name = 'inventaires'
    paginate_by = 20

    def get_queryset(self):
        return Inventaire.objects.select_related('responsable').order_by('-date_debut')


class InventaireDetailView(LoginRequiredMixin, DetailView):
    model = Inventaire
    template_name = 'mouvements/inventaire/detail.html'
    context_object_name = 'inventaire'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['lignes'] = self.object.lignes.select_related('produit', 'lot')
        context['nb_ecarts'] = self.object.lignes.filter(ecart__ne=0).count() if False else 0
        return context


class InventaireCreerView(LoginRequiredMixin, CreateView):
    model = Inventaire
    form_class = InventaireForm
    template_name = 'mouvements/inventaire/form.html'
    success_url = reverse_lazy('mouvements:inventaire-liste')

    def form_valid(self, form):
        form.instance.cree_par = self.request.user
        form.instance.responsable = self.request.user
        messages.success(self.request, _("Inventaire créé avec succès."))
        return super().form_valid(form)
