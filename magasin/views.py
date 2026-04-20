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
def api_plan_temps_reel(request):
    """
    API JSON temps réel — alimente la vue 2D du plan magasin.
    Retourne toutes les matières premières actives avec leurs données
    de stock, emplacement physique, lot, et capacités rayon.
    Endpoint : /magasin/api/plan/
    """
    from produits.models import MatierePremiere
    from mouvements.models import MouvementStock
    from magasin.models import Emplacement as EmplacementMagasin

    matieres = MatierePremiere.objects.filter(actif=True).select_related(
        'unite', 'fournisseur_principal'
    ).order_by('reference')

    # Pré-charger les emplacements magasin indexés par code
    emplacements_map = {
        e.code: e
        for e in EmplacementMagasin.objects.select_related('rayon').all()
    }

    # Pré-charger le dernier mouvement ENTRÉE par matière (une requête groupée)
    from django.db.models import Max
    derniers_ids = (
        MouvementStock.objects
        .filter(type_mouvement='ENTREE')
        .values('matiere_id')
        .annotate(last_id=Max('id'))
        .values_list('last_id', flat=True)
    )
    derniers_mouvements = {
        m.matiere_id: m
        for m in MouvementStock.objects.filter(pk__in=derniers_ids)
    }

    data = []
    for m in matieres:
        stock   = float(m.stock_actuel)
        s_max   = float(m.stock_maximum)
        s_min   = float(m.stock_minimum)
        pc      = float(m.point_commande)

        # Calcul du pourcentage de remplissage
        pct = round(stock / s_max * 100, 1) if s_max > 0 else 0

        # Statut stock
        if stock <= 0:
            statut = "RUPTURE"
        elif pct < 20:
            statut = "CRITIQUE"
        elif pct < 50:
            statut = "ALERTE"
        else:
            statut = "NORMAL"

        # Données emplacement physique magasin
        emp_code = m.emplacement  # ex: "A1-N1"
        emp_obj  = emplacements_map.get(emp_code)
        niveaux  = emp_obj.rayon.nombre_niveaux if emp_obj else 5
        dim_h    = float(emp_obj.rayon.hauteur) if emp_obj else 2.0
        col      = emp_obj.colonne if emp_obj else None
        row      = emp_obj.niveau  if emp_obj else None

        # Données dernier lot (mouvement ENTRÉE)
        dernier_mv = derniers_mouvements.get(m.pk)
        dernier_lot      = dernier_mv.numero_lot if dernier_mv else ""
        date_peremption  = (
            dernier_mv.date_peremption.isoformat()
            if dernier_mv and dernier_mv.date_peremption
            else None
        )

        data.append({
            "id":              m.pk,
            "ref":             m.reference,
            "nom":             m.nom,
            "cat":             m.categorie,
            "zone":            m.zone_stockage,
            "emplacement":     m.emplacement,
            "qty":             stock,
            "max":             s_max,
            "min":             s_min,
            "pc":              pc,
            "qec":             float(m.qec),
            "unit":            m.unite.symbole,
            "prix":            float(m.prix_unitaire),
            "methode":         m.methode_approvisionnement,
            "fournisseur":     m.fournisseur_principal.nom if m.fournisseur_principal else "",
            "pct":             pct,
            "statut":          statut,
            "alerte_commande": stock <= pc,
            "dernier_lot":     dernier_lot,
            "date_peremption": date_peremption,
            "niveaux":         niveaux,
            "dim_L":           1.2,
            "dim_l":           0.8,
            "dim_h":           dim_h,
            "col":             col,
            "row":             row,
        })

    response = JsonResponse({"matieres": data, "count": len(data)})
    response["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response["Pragma"] = "no-cache"
    return response


@login_required
def api_emplacement_detail(request, ref):
    """
    API JSON — Détail complet d'une matière par référence.
    Inclut les 5 derniers mouvements, bons de commande en cours et valeur stock.
    Endpoint : /magasin/api/detail/<ref>/
    """
    from produits.models import MatierePremiere
    from mouvements.models import MouvementStock
    from approvisionnement.models import BonCommande
    from magasin.models import Emplacement as EmplacementMagasin

    matiere = get_object_or_404(
        MatierePremiere.objects.select_related('unite', 'fournisseur_principal'),
        reference=ref, actif=True
    )

    stock = float(matiere.stock_actuel)
    s_max = float(matiere.stock_maximum)
    pc    = float(matiere.point_commande)
    pct   = round(stock / s_max * 100, 1) if s_max > 0 else 0

    if stock <= 0:
        statut = "RUPTURE"
    elif pct < 20:
        statut = "CRITIQUE"
    elif pct < 50:
        statut = "ALERTE"
    else:
        statut = "NORMAL"

    # Emplacement physique magasin
    emp_obj = None
    if matiere.emplacement:
        emp_obj = EmplacementMagasin.objects.select_related('rayon').filter(
            code=matiere.emplacement
        ).first()

    # 5 derniers mouvements
    derniers_mvts = MouvementStock.objects.filter(
        matiere=matiere
    ).select_related('operateur').order_by('-date_mouvement')[:5]

    mouvements_data = [
        {
            "type":      mv.type_mouvement,
            "quantite":  float(mv.quantite),
            "date":      mv.date_mouvement.isoformat(),
            "lot":       mv.numero_lot,
            "operateur": (
                mv.operateur.get_full_name() or mv.operateur.username
                if mv.operateur else "—"
            ),
        }
        for mv in derniers_mvts
    ]

    # Dernier lot depuis le dernier mouvement ENTRÉE
    dernier_mv = MouvementStock.objects.filter(
        matiere=matiere, type_mouvement='ENTREE'
    ).order_by('-id').first()

    # Bons de commande en cours
    bons_en_cours = BonCommande.objects.filter(
        matiere=matiere,
        statut__in=['BROUILLON', 'ENVOYE']
    ).select_related('fournisseur').order_by('-date_creation')[:5]

    bons_data = [
        {
            "reference":          bc.reference,
            "statut":             bc.statut,
            "quantite_commandee": float(bc.quantite_commandee),
            "fournisseur":        bc.fournisseur.nom,
            "date_creation":      bc.date_creation.isoformat(),
            "date_prevue":        bc.date_reception_prevue.isoformat() if bc.date_reception_prevue else None,
        }
        for bc in bons_en_cours
    ]

    response = JsonResponse({
        # Données stock
        "id":              matiere.pk,
        "ref":             matiere.reference,
        "nom":             matiere.nom,
        "cat":             matiere.categorie,
        "zone":            matiere.zone_stockage,
        "emplacement":     matiere.emplacement,
        "qty":             stock,
        "max":             s_max,
        "min":             float(matiere.stock_minimum),
        "pc":              pc,
        "qec":             float(matiere.qec),
        "unit":            matiere.unite.symbole,
        "prix":            float(matiere.prix_unitaire),
        "methode":         matiere.methode_approvisionnement,
        "fournisseur":     matiere.fournisseur_principal.nom if matiere.fournisseur_principal else "",
        "pct":             pct,
        "statut":          statut,
        "alerte_commande": stock <= pc,
        "valeur_stock":    round(stock * float(matiere.prix_unitaire), 2),
        # Lot
        "dernier_lot":     dernier_mv.numero_lot if dernier_mv else "",
        "date_peremption": (
            dernier_mv.date_peremption.isoformat()
            if dernier_mv and dernier_mv.date_peremption else None
        ),
        # Emplacement physique
        "niveaux": emp_obj.rayon.nombre_niveaux if emp_obj else 5,
        "dim_L":   1.2,
        "dim_l":   0.8,
        "dim_h":   float(emp_obj.rayon.hauteur) if emp_obj else 2.0,
        "col":     emp_obj.colonne if emp_obj else None,
        "row":     emp_obj.niveau  if emp_obj else None,
        # Historique et commandes
        "mouvements":   mouvements_data,
        "bons_en_cours": bons_data,
    })
    response["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response




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
