"""produits/views.py"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.db.models import Q
from django.contrib import messages
from django.utils.translation import gettext_lazy as _

from .models import Fournisseur, UnitesMesure, MatierePremiere


# ============================================================
# MATIÈRES PREMIÈRES
# ============================================================

class MatiereListeView(LoginRequiredMixin, ListView):
    model               = MatierePremiere
    template_name       = "produits/matiere/liste.html"
    context_object_name = "matieres"
    paginate_by         = 25

    def get_queryset(self):
        qs = MatierePremiere.objects.select_related("unite", "fournisseur_principal")
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(Q(reference__icontains=q) | Q(nom__icontains=q))
        categorie = self.request.GET.get("categorie")
        if categorie:
            qs = qs.filter(categorie=categorie)
        methode = self.request.GET.get("methode")
        if methode:
            qs = qs.filter(methode_approvisionnement=methode)
        actif = self.request.GET.get("actif", "1")
        qs = qs.filter(actif=(actif == "1"))
        return qs.order_by("reference")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["categories"] = MatierePremiere.Categorie.choices
        ctx["methodes"]   = MatierePremiere.MethodeApprovisionnement.choices
        return ctx


class MatiereDetailView(LoginRequiredMixin, DetailView):
    model               = MatierePremiere
    template_name       = "produits/matiere/detail.html"
    context_object_name = "matiere"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["mouvements_recents"] = self.object.mouvements.order_by("-date_mouvement")[:15]
        ctx["bons_commande"]      = self.object.bons_commande.order_by("-date_creation")[:10]
        return ctx


class MatiereCreerView(LoginRequiredMixin, CreateView):
    model         = MatierePremiere
    template_name = "produits/matiere/form.html"
    fields        = [
        "reference", "nom", "description", "categorie",
        "unite", "fournisseur_principal", "prix_unitaire",
        "stock_actuel", "stock_minimum", "stock_maximum", "stock_securite",
        "methode_approvisionnement", "point_commande", "qec",
        "delai_livraison_jours", "periode_reappro_jours", "taux_rebut",
        "zone_stockage", "emplacement", "actif"
    ]
    success_url = reverse_lazy("produits:matiere-liste")

    def form_valid(self, form):
        messages.success(self.request, _("Matière première créée avec succès."))
        return super().form_valid(form)


class MatiereModifierView(LoginRequiredMixin, UpdateView):
    model         = MatierePremiere
    template_name = "produits/matiere/form.html"
    fields        = [
        "nom", "description", "categorie",
        "unite", "fournisseur_principal", "prix_unitaire",
        "stock_actuel", "stock_minimum", "stock_maximum", "stock_securite",
        "methode_approvisionnement", "point_commande", "qec",
        "delai_livraison_jours", "periode_reappro_jours", "taux_rebut",
        "zone_stockage", "emplacement", "actif"
    ]

    def get_success_url(self):
        messages.success(self.request, _("Matière première mise à jour."))
        return reverse_lazy("produits:matiere-detail", kwargs={"pk": self.object.pk})


# ============================================================
# FOURNISSEURS
# ============================================================

class FournisseurListeView(LoginRequiredMixin, ListView):
    model               = Fournisseur
    template_name       = "produits/fournisseur/liste.html"
    context_object_name = "fournisseurs"
    paginate_by         = 25

    def get_queryset(self):
        qs = Fournisseur.objects.all()
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(Q(nom__icontains=q) | Q(ville__icontains=q))
        if self.request.GET.get("actif") == "0":
            qs = qs.filter(actif=False)
        else:
            qs = qs.filter(actif=True)
        return qs.order_by("nom")


class FournisseurCreerView(LoginRequiredMixin, CreateView):
    model         = Fournisseur
    template_name = "produits/fournisseur/form.html"
    fields        = ["nom", "contact", "email", "telephone", "adresse", "ville", "pays", "actif"]
    success_url   = reverse_lazy("produits:fournisseur-liste")

    def form_valid(self, form):
        messages.success(self.request, _("Fournisseur créé avec succès."))
        return super().form_valid(form)


class FournisseurModifierView(LoginRequiredMixin, UpdateView):
    model         = Fournisseur
    template_name = "produits/fournisseur/form.html"
    fields        = ["nom", "contact", "email", "telephone", "adresse", "ville", "pays", "actif"]
    success_url   = reverse_lazy("produits:fournisseur-liste")

    def form_valid(self, form):
        messages.success(self.request, _("Fournisseur mis à jour."))
        return super().form_valid(form)


# ============================================================
# UNITÉS DE MESURE
# ============================================================

class UniteListeView(LoginRequiredMixin, ListView):
    model               = UnitesMesure
    template_name       = "produits/unite/liste.html"
    context_object_name = "unites"


# ============================================================
# API JSON — recherche autocomplete
# ============================================================

def matiere_search_api(request):
    """Recherche rapide pour Select2 / autocomplete."""
    from django.contrib.auth.decorators import login_required
    q = request.GET.get("q", "")
    matieres = MatierePremiere.objects.filter(
        Q(reference__icontains=q) | Q(nom__icontains=q),
        actif=True
    )[:20]
    data = [
        {
            "id":            m.pk,
            "reference":     m.reference,
            "nom":           m.nom,
            "stock_actuel":  float(m.stock_actuel),
            "unite":         m.unite.symbole if m.unite else "",
            "prix_unitaire": float(m.prix_unitaire),
        }
        for m in matieres
    ]
    return JsonResponse({"results": data})
