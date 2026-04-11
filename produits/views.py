"""
App Produits - Vues
Gestion des produits, fournisseurs, catégories, unités
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
)
from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Sum, Avg, Count, F
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from .models import Produit, Fournisseur, CategorieProduit, UniteMesure, LotProduit, TarifFournisseur
from .forms import (
    ProduitForm, FournisseurForm, CategorieProduitForm,
    UniteMesureForm, LotProduitForm, RechercheProduitsForm
)


# ============================================================
# PRODUITS
# ============================================================

class ProduitListeView(LoginRequiredMixin, ListView):
    """Liste de tous les produits avec filtres avancés."""
    model = Produit
    template_name = 'produits/produit/liste.html'
    context_object_name = 'produits'
    paginate_by = 25

    def get_queryset(self):
        qs = Produit.objects.select_related(
            'categorie', 'fournisseur_principal', 'unite_stock', 'emplacement'
        ).filter(statut=Produit.Statut.ACTIF)

        # Filtres
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(
                Q(code__icontains=q) |
                Q(designation__icontains=q) |
                Q(code_barre__icontains=q)
            )
        categorie = self.request.GET.get('categorie')
        if categorie:
            qs = qs.filter(categorie_id=categorie)

        statut_stock = self.request.GET.get('statut_stock')
        if statut_stock == 'alerte':
            qs = qs.filter(stock_actuel__lte=F('stock_minimum'), stock_actuel__gt=0)
        elif statut_stock == 'rupture':
            qs = qs.filter(stock_actuel__lte=0)
        elif statut_stock == 'surstock':
            qs = qs.filter(stock_actuel__gt=F('stock_maximum'), stock_maximum__gt=0)

        classe = self.request.GET.get('classe_abc')
        if classe:
            qs = qs.filter(classe_abc=classe)

        return qs.order_by('designation')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = CategorieProduit.objects.filter(est_actif=True)
        context['total_produits'] = Produit.objects.filter(statut=Produit.Statut.ACTIF).count()
        context['nb_alertes'] = Produit.objects.filter(
            stock_actuel__lte=F('stock_minimum'), stock_actuel__gt=0, statut=Produit.Statut.ACTIF
        ).count()
        context['nb_ruptures'] = Produit.objects.filter(
            stock_actuel__lte=0, statut=Produit.Statut.ACTIF
        ).count()
        context['valeur_totale_stock'] = Produit.objects.filter(
            statut=Produit.Statut.ACTIF
        ).aggregate(
            total=Sum(F('stock_actuel') * F('prix_unitaire_revient'))
        )['total'] or 0
        return context


class ProduitDetailView(LoginRequiredMixin, DetailView):
    """Fiche complète d'un produit."""
    model = Produit
    template_name = 'produits/produit/detail.html'
    context_object_name = 'produit'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        produit = self.object
        context['lots'] = produit.lots.filter(
            statut=LotProduit.Statut.DISPONIBLE
        ).order_by('date_peremption')
        context['tarifs'] = produit.tarifs.all().order_by('-date_validite_debut')
        context['mouvements_recents'] = produit.mouvements.select_related(
            'cree_par'
        ).order_by('-date_mouvement')[:10]
        return context


class ProduitCreerView(LoginRequiredMixin, CreateView):
    """Créer un nouveau produit."""
    model = Produit
    form_class = ProduitForm
    template_name = 'produits/produit/form.html'

    def get_success_url(self):
        messages.success(self.request, _(f"Produit '{self.object.designation}' créé avec succès."))
        return reverse_lazy('produits:produit-detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        form.instance.cree_par = self.request.user
        return super().form_valid(form)


class ProduitModifierView(LoginRequiredMixin, UpdateView):
    """Modifier un produit existant."""
    model = Produit
    form_class = ProduitForm
    template_name = 'produits/produit/form.html'

    def get_success_url(self):
        messages.success(self.request, _("Produit mis à jour avec succès."))
        return reverse_lazy('produits:produit-detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        form.instance.modifie_par = self.request.user
        return super().form_valid(form)


# ============================================================
# FOURNISSEURS
# ============================================================

class FournisseurListeView(LoginRequiredMixin, ListView):
    """Liste des fournisseurs."""
    model = Fournisseur
    template_name = 'produits/fournisseur/liste.html'
    context_object_name = 'fournisseurs'
    paginate_by = 25

    def get_queryset(self):
        qs = Fournisseur.objects.all()
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(
                Q(code__icontains=q) |
                Q(raison_sociale__icontains=q) |
                Q(ville__icontains=q)
            )
        statut = self.request.GET.get('statut')
        if statut:
            qs = qs.filter(statut=statut)
        return qs.order_by('raison_sociale')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['statuts'] = Fournisseur.Statut.choices
        context['nb_actifs'] = Fournisseur.objects.filter(statut=Fournisseur.Statut.ACTIF).count()
        return context


class FournisseurDetailView(LoginRequiredMixin, DetailView):
    """Fiche fournisseur complète."""
    model = Fournisseur
    template_name = 'produits/fournisseur/detail.html'
    context_object_name = 'fournisseur'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['produits'] = self.object.produits_principaux.filter(
            statut=Produit.Statut.ACTIF
        )
        context['tarifs'] = self.object.tarifs.order_by('-date_validite_debut')[:10]
        return context


class FournisseurCreerView(LoginRequiredMixin, CreateView):
    model = Fournisseur
    form_class = FournisseurForm
    template_name = 'produits/fournisseur/form.html'
    success_url = reverse_lazy('produits:fournisseur-liste')

    def form_valid(self, form):
        form.instance.cree_par = self.request.user
        messages.success(self.request, _("Fournisseur créé avec succès."))
        return super().form_valid(form)


class FournisseurModifierView(LoginRequiredMixin, UpdateView):
    model = Fournisseur
    form_class = FournisseurForm
    template_name = 'produits/fournisseur/form.html'
    success_url = reverse_lazy('produits:fournisseur-liste')

    def form_valid(self, form):
        form.instance.modifie_par = self.request.user
        messages.success(self.request, _("Fournisseur mis à jour avec succès."))
        return super().form_valid(form)


# ============================================================
# CATÉGORIES & UNITÉS
# ============================================================

class CategorieListeView(LoginRequiredMixin, ListView):
    model = CategorieProduit
    template_name = 'produits/categorie/liste.html'
    context_object_name = 'categories'

    def get_queryset(self):
        return CategorieProduit.objects.filter(parent=None).prefetch_related('sous_categories')


class UniteMesureListeView(LoginRequiredMixin, ListView):
    model = UniteMesure
    template_name = 'produits/unite/liste.html'
    context_object_name = 'unites'


# ============================================================
# LOTS DE PRODUITS
# ============================================================

class LotListeView(LoginRequiredMixin, ListView):
    """Liste des lots en stock avec alertes péremption."""
    model = LotProduit
    template_name = 'produits/lot/liste.html'
    context_object_name = 'lots'
    paginate_by = 30

    def get_queryset(self):
        qs = LotProduit.objects.select_related('produit').filter(
            statut=LotProduit.Statut.DISPONIBLE,
            quantite_restante__gt=0,
        )
        # Alertes péremption < 90 jours
        if self.request.GET.get('alerte_peremption'):
            date_limite = timezone.now().date() + timezone.timedelta(days=90)
            qs = qs.filter(date_peremption__lte=date_limite)
        return qs.order_by('date_peremption')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        date_alerte = timezone.now().date() + timezone.timedelta(days=90)
        context['nb_proches_peremption'] = LotProduit.objects.filter(
            statut=LotProduit.Statut.DISPONIBLE,
            date_peremption__lte=date_alerte,
            date_peremption__gte=timezone.now().date(),
            quantite_restante__gt=0,
        ).count()
        context['nb_perimes'] = LotProduit.objects.filter(
            statut=LotProduit.Statut.DISPONIBLE,
            date_peremption__lt=timezone.now().date(),
            quantite_restante__gt=0,
        ).count()
        return context


# ============================================================
# API JSON
# ============================================================

@login_required
def produit_search_api(request):
    """Recherche produit pour Select2/autocomplete."""
    q = request.GET.get('q', '')
    produits = Produit.objects.filter(
        Q(code__icontains=q) | Q(designation__icontains=q),
        statut=Produit.Statut.ACTIF,
    )[:20]
    data = [
        {
            'id': p.pk,
            'code': p.code,
            'designation': p.designation,
            'stock_actuel': float(p.stock_actuel),
            'unite': str(p.unite_stock),
            'prix': float(p.prix_unitaire_revient),
        }
        for p in produits
    ]
    return JsonResponse({'results': data})
