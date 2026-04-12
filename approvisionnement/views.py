"""approvisionnement/views.py"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db.models import Q, Sum

from .models import BonCommande, PlanMRP
from produits.models import MatierePremiere


# ============================================================
# TABLEAU DE BORD APPROVISIONNEMENT
# ============================================================

class ApproDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "approvisionnement/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["nb_commandes_en_attente"] = BonCommande.objects.filter(
            statut=BonCommande.Statut.BROUILLON
        ).count()
        ctx["nb_matieres_en_alerte"] = MatierePremiere.objects.filter(
            actif=True, stock_actuel__lte=MatierePremiere.stock_minimum.field.default
        ).count()
        ctx["commandes"] = BonCommande.objects.select_related(
            "matiere", "fournisseur"
        ).order_by("-date_creation")[:8]
        ctx["suggestions"] = []   # alimenté par les services de calcul
        return ctx


# ============================================================
# BONS DE COMMANDE
# ============================================================

class BonCommandeListeView(LoginRequiredMixin, ListView):
    model               = BonCommande
    template_name       = "approvisionnement/commande/liste.html"
    context_object_name = "commandes"
    paginate_by         = 25

    def get_queryset(self):
        qs = BonCommande.objects.select_related("matiere", "fournisseur", "cree_par")
        statut = self.request.GET.get("statut")
        if statut:
            qs = qs.filter(statut=statut)
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(
                Q(reference__icontains=q) |
                Q(matiere__nom__icontains=q) |
                Q(fournisseur__nom__icontains=q)
            )
        return qs.order_by("-date_creation")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["statuts"] = BonCommande.Statut.choices
        ctx["montant_total_en_cours"] = BonCommande.objects.filter(
            statut__in=[BonCommande.Statut.ENVOYE, BonCommande.Statut.CONFIRME]
        ).aggregate(total=Sum("montant_total"))["total"] or 0
        return ctx


class BonCommandeDetailView(LoginRequiredMixin, DetailView):
    model               = BonCommande
    template_name       = "approvisionnement/commande/detail.html"
    context_object_name = "commande"


class BonCommandeCreerView(LoginRequiredMixin, CreateView):
    model         = BonCommande
    template_name = "approvisionnement/commande/form.html"
    fields        = [
        "matiere", "fournisseur", "quantite_commandee", "prix_unitaire",
        "methode_declenchement", "statut",
        "date_reception_prevue", "notes"
    ]

    def form_valid(self, form):
        form.instance.cree_par = self.request.user
        messages.success(self.request, _("Bon de commande créé avec succès."))
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("approvisionnement:commande-detail", kwargs={"pk": self.object.pk})


class BonCommandeModifierView(LoginRequiredMixin, UpdateView):
    model         = BonCommande
    template_name = "approvisionnement/commande/form.html"
    fields        = [
        "matiere", "fournisseur", "quantite_commandee", "prix_unitaire",
        "methode_declenchement", "statut",
        "date_reception_prevue", "date_reception_reelle", "notes"
    ]

    def form_valid(self, form):
        messages.success(self.request, _("Bon de commande mis à jour."))
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("approvisionnement:commande-detail", kwargs={"pk": self.object.pk})


# ============================================================
# PLANS MRP
# ============================================================

class PlanMRPListeView(LoginRequiredMixin, ListView):
    model               = PlanMRP
    template_name       = "approvisionnement/mrp/liste.html"
    context_object_name = "plans"
    paginate_by         = 30

    def get_queryset(self):
        return PlanMRP.objects.select_related("matiere").order_by("-periode")


class PlanMRPCreerView(LoginRequiredMixin, CreateView):
    model         = PlanMRP
    template_name = "approvisionnement/mrp/form.html"
    fields        = [
        "matiere", "periode", "besoin_brut", "stock_debut_periode",
        "besoin_net", "quantite_proposee", "stock_fin_periode", "statut"
    ]
    success_url = reverse_lazy("approvisionnement:mrp-liste")

    def form_valid(self, form):
        messages.success(self.request, _("Ligne MRP créée."))
        return super().form_valid(form)


# ============================================================
# MÉTHODES — pages de calcul
# ============================================================

class ReapproFixeView(LoginRequiredMixin, TemplateView):
    template_name = "approvisionnement/methodes/reappro_fixe.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["matieres"] = MatierePremiere.objects.filter(
            methode_approvisionnement="REAPPRO_FIXE", actif=True
        ).select_related("unite", "fournisseur_principal")
        return ctx


class PointCommandeView(LoginRequiredMixin, TemplateView):
    template_name = "approvisionnement/methodes/point_commande.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from django.db.models import F
        ctx["matieres_en_alerte"] = MatierePremiere.objects.filter(
            methode_approvisionnement="POINT_COMMANDE",
            actif=True,
            stock_actuel__lte=F("point_commande"),
        ).select_related("unite", "fournisseur_principal")
        ctx["toutes_matieres"] = MatierePremiere.objects.filter(
            methode_approvisionnement="POINT_COMMANDE", actif=True
        ).select_related("unite")
        return ctx


class RecompletementView(LoginRequiredMixin, TemplateView):
    template_name = "approvisionnement/methodes/recompletement.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["matieres"] = MatierePremiere.objects.filter(
            methode_approvisionnement="RECOMPLETEMENT", actif=True
        ).select_related("unite", "fournisseur_principal")
        return ctx
