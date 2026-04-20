"""produits/views.py"""
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.views import View
from django.shortcuts import redirect
from django.urls import reverse_lazy, reverse
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


class MatiereChoisirMethodeView(LoginRequiredMixin, View):
    """Étape 0 : choix de la méthode avant création."""
    template_name = "produits/matiere/choisir_methode.html"

    def get(self, request):
        from django.shortcuts import render
        return render(request, self.template_name)

    def post(self, request):
        from django.shortcuts import render, redirect
        from django.urls import reverse
        methode = request.POST.get("methode")
        if methode not in MatierePremiere.MethodeApprovisionnement.values:
            messages.error(request, "Méthode invalide.")
            return redirect("produits:matiere-choisir-methode")
        return redirect(reverse("produits:matiere-create") + f"?methode={methode}")


class MatiereCreerView(LoginRequiredMixin, CreateView):
    model         = MatierePremiere
    template_name = "produits/matiere/form_step1.html"
    fields        = [
        "reference", "nom", "description", "categorie",
        "unite", "fournisseur_principal", "prix_unitaire",
        "stock_actuel", "stock_minimum", "stock_maximum",
        "stock_securite", "zone_stockage", "emplacement", "actif"
    ]

    def get_initial(self):
        initial = super().get_initial()
        initial["methode_approvisionnement"] = self.request.GET.get("methode", "POINT_COMMANDE")
        return initial

    def get_context_data(self, **kwargs):
        from django.urls import reverse
        ctx = super().get_context_data(**kwargs)
        ctx["methode_choisie"] = self.request.GET.get("methode", "POINT_COMMANDE")
        ctx["methode_label"] = dict(
            MatierePremiere.MethodeApprovisionnement.choices
        ).get(ctx["methode_choisie"], "")
        ctx["step"]       = 1
        ctx["step_total"] = 2
        ctx["step_range"] = range(1, 3)
        return ctx

    def form_valid(self, form):
        from django.urls import reverse
        methode = self.request.GET.get("methode", "POINT_COMMANDE")
        form.instance.methode_approvisionnement = methode
        self.object = form.save()
        messages.info(
            self.request,
            f"Étape 1 complète. Configurez maintenant les paramètres "
            f"d'approvisionnement pour « {self.object.nom} »."
        )
        return redirect(reverse("produits:matiere-parametres", kwargs={"pk": self.object.pk}))


# ============================================================
# PARAMÈTRES PAR MÉTHODE (step 2)
# ============================================================

PARAMS_PAR_METHODE = {
    "POINT_COMMANDE": {
        "fields":      ["point_commande", "qec", "delai_livraison_jours"],
        "description": "Définissez le seuil de déclenchement (ROP), la quantité économique de commande (QEC) et le délai fournisseur.",
        "icon":        "bi-graph-down-arrow",
        "formulas": {
            "point_commande": "ROP = Consommation journalière × Délai livraison + Stock sécurité",
            "qec":            "QEC = √(2 × D × K / (h × Pu))  — Formule de Wilson",
        },
    },
    "REAPPRO_FIXE": {
        "fields":      ["qec", "periode_reappro_jours", "delai_livraison_jours"],
        "description": "Définissez la quantité fixe commandée (Q), la période de réapprovisionnement (T) et le délai fournisseur.",
        "icon":        "bi-calendar-check",
        "formulas": {
            "qec": "Q fixe commandée à chaque déclenchement",
        },
    },
    "RECOMPLETEMENT": {
        "fields":      ["stock_maximum", "periode_reappro_jours", "delai_livraison_jours"],
        "description": "Définissez le niveau cible (S = stock maximum), la période de révision (T) et le délai fournisseur. À chaque révision on commande S − stock actuel.",
        "icon":        "bi-arrow-repeat",
        "formulas": {
            "stock_maximum": "S = Niveau de recomplètement cible",
        },
    },
    "MRP": {
        "fields":      ["taux_rebut", "delai_livraison_jours", "periode_reappro_jours"],
        "description": "Configurez le taux de rebut de production et le délai fournisseur. Les quantités seront calculées par le plan MRP.",
        "icon":        "bi-diagram-3",
        "formulas": {
            "taux_rebut": "Besoin brut ajusté = Besoin net / (1 − taux_rebut)",
        },
    },
}


class MatiereParametresMethodeView(LoginRequiredMixin, UpdateView):
    """Étape 2 : paramètres spécifiques à la méthode d'approvisionnement."""
    model         = MatierePremiere
    template_name = "produits/matiere/form_step2.html"

    def get_object(self, queryset=None):
        if not hasattr(self, "_object"):
            self._object = super().get_object(queryset)
        return self._object

    def get_fields_for_method(self):
        methode = self.get_object().methode_approvisionnement
        return PARAMS_PAR_METHODE.get(methode, {}).get("fields", [])

    def get_form_class(self):
        from django.forms import modelform_factory
        return modelform_factory(MatierePremiere, fields=self.get_fields_for_method())

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        methode = self.object.methode_approvisionnement
        ctx["methode_config"] = PARAMS_PAR_METHODE.get(methode, {})
        ctx["methode_label"]  = self.object.get_methode_approvisionnement_display()
        ctx["step"]           = 2
        ctx["step_total"]     = 2
        ctx["step_range"]     = range(1, 3)
        return ctx

    def form_valid(self, form):
        from django.urls import reverse
        form.save()
        messages.success(
            self.request,
            f"Matière « {self.object.nom} » créée et configurée avec succès."
        )
        return redirect(reverse("produits:matiere-detail", kwargs={"pk": self.object.pk}))


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


# ============================================================
# SUPPRESSION MATIÈRE PREMIÈRE (admin uniquement)
# ============================================================

class MatiereSuppressionView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model         = MatierePremiere
    template_name = "produits/matiere/confirm_delete.html"
    success_url   = reverse_lazy("produits:matiere-liste")

    def test_func(self):
        return self.request.user.est_admin

    def form_valid(self, form):
        messages.success(self.request, f"Matière « {self.object.nom} » supprimée.")
        return super().form_valid(form)
