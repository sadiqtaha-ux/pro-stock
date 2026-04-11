"""mouvements/views.py"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from .models import MouvementStock


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
        messages.success(self.request, _("Mouvement enregistré avec succès."))
        return super().form_valid(form)


class EntreeListeView(LoginRequiredMixin, ListView):
    """Alias — filtre uniquement les entrées."""
    model               = MouvementStock
    template_name       = "mouvements/entrees/liste.html"
    context_object_name = "mouvements"
    paginate_by         = 30

    def get_queryset(self):
        return MouvementStock.objects.filter(
            type_mouvement=MouvementStock.TypeMouvement.ENTREE
        ).select_related("matiere", "operateur").order_by("-date_mouvement")


class SortieListeView(LoginRequiredMixin, ListView):
    """Alias — filtre uniquement les sorties."""
    model               = MouvementStock
    template_name       = "mouvements/sorties/liste.html"
    context_object_name = "mouvements"
    paginate_by         = 30

    def get_queryset(self):
        return MouvementStock.objects.filter(
            type_mouvement=MouvementStock.TypeMouvement.SORTIE
        ).select_related("matiere", "operateur").order_by("-date_mouvement")
