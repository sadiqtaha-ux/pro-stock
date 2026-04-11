"""
App Magasin - Vues
Vue 2D interactive du magasin, gestion des emplacements
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.db.models import Count, Q
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from .models import ZoneStockage, Rayon, Emplacement, PlanMagasin
from .forms import ZoneStockageForm, RayonForm, EmplacementForm


# ============================================================
# VUE 2D DU MAGASIN
# ============================================================

class PlanMagasinView(LoginRequiredMixin, TemplateView):
    """
    Vue 2D interactive du magasin.
    Affiche les zones, rayons et emplacements sur un plan graphique.
    Utilise Canvas HTML5 / SVG pour le rendu.
    """
    template_name = 'magasin/plan/vue_2d.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['plan'] = PlanMagasin.objects.filter(est_actif=True).first()
        context['zones'] = ZoneStockage.objects.filter(est_actif=True).prefetch_related('rayons')
        context['stats'] = {
            'total_emplacements': Emplacement.objects.count(),
            'libres': Emplacement.objects.filter(statut=Emplacement.StatutEmplacement.LIBRE).count(),
            'occupes': Emplacement.objects.filter(statut=Emplacement.StatutEmplacement.OCCUPE).count(),
            'bloques': Emplacement.objects.filter(statut=Emplacement.StatutEmplacement.BLOQUE).count(),
        }
        return context


@login_required
def api_plan_data(request):
    """
    API JSON : Données du plan 2D pour le rendu Canvas/SVG.
    Renvoie toutes les zones et emplacements avec leurs positions.
    """
    zones = ZoneStockage.objects.filter(est_actif=True).prefetch_related(
        'rayons__emplacements__produits'
    )

    data = []
    for zone in zones:
        zone_data = {
            'id': zone.pk,
            'code': zone.code,
            'libelle': zone.libelle,
            'type': zone.type_zone,
            'couleur': zone.couleur,
            'x': zone.position_x,
            'y': zone.position_y,
            'w': zone.largeur,
            'h': zone.hauteur,
            'rayons': [],
        }
        for rayon in zone.rayons.filter(est_actif=True):
            rayon_data = {
                'id': rayon.pk,
                'code': rayon.code,
                'x': rayon.position_x,
                'y': rayon.position_y,
                'w': rayon.largeur,
                'h': rayon.hauteur,
                'emplacements': [
                    {
                        'id': emp.pk,
                        'code': emp.code,
                        'statut': emp.statut,
                        'niveau': emp.niveau,
                        'colonne': emp.colonne,
                        'produit': emp.produit_stocke.designation if emp.produit_stocke else None,
                    }
                    for emp in rayon.emplacements.all()
                ]
            }
            zone_data['rayons'].append(rayon_data)
        data.append(zone_data)

    return JsonResponse({'zones': data})


@login_required
def api_emplacement_detail(request, pk):
    """API JSON : Détail d'un emplacement (pour tooltip/popup sur le plan)."""
    emp = get_object_or_404(Emplacement, pk=pk)
    produits = emp.produits.filter(statut='ACTIF').values(
        'code', 'designation', 'stock_actuel', 'unite_stock__code'
    )
    return JsonResponse({
        'id': emp.pk,
        'code': emp.code,
        'statut': emp.statut,
        'statut_display': emp.get_statut_display(),
        'rayon': str(emp.rayon),
        'niveau': emp.niveau,
        'colonne': emp.colonne,
        'produits': list(produits),
        'notes': emp.notes,
    })


# ============================================================
# ZONES
# ============================================================

class ZoneListeView(LoginRequiredMixin, ListView):
    model = ZoneStockage
    template_name = 'magasin/zone/liste.html'
    context_object_name = 'zones'

    def get_queryset(self):
        return ZoneStockage.objects.filter(est_actif=True).annotate(
            nb_rayons=Count('rayons'),
        ).prefetch_related('rayons')


class ZoneDetailView(LoginRequiredMixin, DetailView):
    model = ZoneStockage
    template_name = 'magasin/zone/detail.html'
    context_object_name = 'zone'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['rayons'] = self.object.rayons.filter(est_actif=True).annotate(
            nb_emplacements=Count('emplacements'),
            nb_libres=Count('emplacements', filter=Q(emplacements__statut='LIBRE')),
        )
        return context


class ZoneCreerView(LoginRequiredMixin, CreateView):
    model = ZoneStockage
    form_class = ZoneStockageForm
    template_name = 'magasin/zone/form.html'
    success_url = reverse_lazy('magasin:zone-liste')

    def form_valid(self, form):
        form.instance.cree_par = self.request.user
        messages.success(self.request, _("Zone créée avec succès."))
        return super().form_valid(form)


# ============================================================
# RAYONS
# ============================================================

class RayonListeView(LoginRequiredMixin, ListView):
    model = Rayon
    template_name = 'magasin/rayon/liste.html'
    context_object_name = 'rayons'

    def get_queryset(self):
        return Rayon.objects.select_related('zone').filter(est_actif=True).annotate(
            nb_emplacements=Count('emplacements'),
        )


class RayonCreerView(LoginRequiredMixin, CreateView):
    model = Rayon
    form_class = RayonForm
    template_name = 'magasin/rayon/form.html'
    success_url = reverse_lazy('magasin:rayon-liste')

    def form_valid(self, form):
        form.instance.cree_par = self.request.user
        messages.success(self.request, _("Rayon créé avec succès."))
        return super().form_valid(form)


# ============================================================
# EMPLACEMENTS
# ============================================================

class EmplacementListeView(LoginRequiredMixin, ListView):
    model = Emplacement
    template_name = 'magasin/emplacement/liste.html'
    context_object_name = 'emplacements'
    paginate_by = 50

    def get_queryset(self):
        qs = Emplacement.objects.select_related('rayon', 'rayon__zone').filter(est_actif=True)
        statut = self.request.GET.get('statut')
        if statut:
            qs = qs.filter(statut=statut)
        zone = self.request.GET.get('zone')
        if zone:
            qs = qs.filter(rayon__zone_id=zone)
        return qs.order_by('rayon__zone', 'rayon', 'niveau', 'colonne')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['statuts'] = Emplacement.StatutEmplacement.choices
        context['zones'] = ZoneStockage.objects.filter(est_actif=True)
        return context


class EmplacementCreerView(LoginRequiredMixin, CreateView):
    model = Emplacement
    form_class = EmplacementForm
    template_name = 'magasin/emplacement/form.html'
    success_url = reverse_lazy('magasin:emplacement-liste')

    def form_valid(self, form):
        form.instance.cree_par = self.request.user
        messages.success(self.request, _("Emplacement créé avec succès."))
        return super().form_valid(form)
