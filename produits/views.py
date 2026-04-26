"""produits/views.py"""
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.views import View
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, F, Sum, Case, When, Value, CharField
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.decorators import login_required
import csv
import json

from core.mixins import KanbanListMixin, ExportMixin
from core.models import JournalActivite
from core.utils import log_action
from .models import Fournisseur, UnitesMesure, MatierePremiere, ProduitFini, Nomenclature, LigneNomenclature
from .forms import (
    MatierePremiereBaseForm,
    MatierePremiereForm,
    MatierePremiereStep1Form,
    get_formulaire_methode,
    FORMULAIRES_PAR_METHODE,
    ProduitFiniForm,
    NomenclatureForm,
    LigneNomenclatureForm,
)


class UnitValidationMixin:
    """Fournit des tables de correspondance Article -> Autorise Décimales pour le JS."""
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        unites = UnitesMesure.objects.all().values('id', 'nom', 'autorise_decimales')
        unites_map = {u['id']: u['autorise_decimales'] for u in unites}
        context['unites_json'] = json.dumps(unites_map)
        
        # Mapping Matière ID -> Autorise Décimales
        matieres = MatierePremiere.objects.all().values('id', 'unite_id')
        matieres_map = {m['id']: unites_map.get(m['unite_id'], True) for m in matieres}
        context['matieres_decimales_json'] = json.dumps(matieres_map)
        
        # Mapping Produit Fini ID -> Autorise Décimales
        produits = ProduitFini.objects.all().values('id', 'unite_id')
        produits_map = {p['id']: unites_map.get(p['unite_id'], True) for p in produits}
        context['produits_decimales_json'] = json.dumps(produits_map)
        
        return context



# ============================================================
# MATIÈRES PREMIÈRES
# ============================================================

class MatiereListeView(LoginRequiredMixin, KanbanListMixin, ExportMixin, ListView):
    model               = MatierePremiere
    template_name       = "produits/matiere/liste.html"
    kanban_template_name = "produits/matiere/kanban.html"
    context_object_name = "matieres"
    paginate_by         = 25
    export_fields       = ['reference', 'nom', 'categorie', 'stock_actuel', 'unite__symbole', 'stock_minimum', 'classe_abc', 'methode_approvisionnement', 'fournisseur_principal__nom']
    export_headers      = ['Référence', 'Nom', 'Catégorie', 'Stock Actuel', 'Unité', 'Stock Min', 'ABC', 'Méthode Appro', 'Fournisseur']

    def get_queryset(self):
        qs = MatierePremiere.objects.select_related("unite", "fournisseur_principal").annotate(
            calculated_statut=Case(
                When(stock_actuel__lte=0, then=Value('RUPTURE')),
                When(stock_actuel__lte=F('stock_minimum'), then=Value('CRITIQUE')),
                When(Q(stock_actuel__lt=F('point_commande')) | Q(stock_maximum__gt=0, stock_actuel__lt=F('stock_maximum')*0.5), then=Value('ALERTE')),
                default=Value('NORMAL'),
                output_field=CharField(),
            )
        )
        
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(Q(reference__icontains=q) | Q(nom__icontains=q))
        
        categorie = self.request.GET.get("categorie")
        if categorie:
            qs = qs.filter(categorie=categorie)
            
        fournisseur = self.request.GET.get("fournisseur")
        if fournisseur:
            qs = qs.filter(fournisseur_principal_id=fournisseur)
            
        abc = self.request.GET.get("abc")
        if abc:
            qs = qs.filter(classe_abc=abc)
            
        methode = self.request.GET.get("methode")
        if methode:
            qs = qs.filter(methode_approvisionnement=methode)
            
        statut_stock = self.request.GET.get("statut_stock")
        if statut_stock:
            qs = qs.filter(calculated_statut=statut_stock)
            
        actif = self.request.GET.get("actif")
        if actif == "0":
            qs = qs.filter(actif=False)
        elif actif == "1":
            qs = qs.filter(actif=True)
            
        return qs.order_by("reference")

    def get(self, request, *args, **kwargs):
        export_type = request.GET.get('export')
        if export_type == 'csv':
            return self.render_to_csv(self.get_queryset(), filename_prefix="matieres")
        elif export_type == 'pdf':
            return self.render_to_pdf(self.get_queryset(), title="Catalogue des Matières Premières", filename_prefix="matieres")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["categories"] = MatierePremiere.Categorie.choices
        ctx["methodes"]   = MatierePremiere.MethodeApprovisionnement.choices
        ctx["fournisseurs"] = Fournisseur.objects.filter(actif=True)
        ctx["abc_choices"] = MatierePremiere.ClasseABC.choices
        ctx["statut_stock_choices"] = [
            ('RUPTURE', 'Rupture'),
            ('CRITIQUE', 'Critique'),
            ('ALERTE', 'Alerte'),
            ('NORMAL', 'Normal'),
        ]
        return ctx


class MatiereDetailView(LoginRequiredMixin, DetailView):
    model               = MatierePremiere
    template_name       = "produits/matiere/detail.html"
    context_object_name = "matiere"

    def get_context_data(self, **kwargs):
        from produits.abc_recommandation import recommander_methode_approvisionnement
        ctx = super().get_context_data(**kwargs)
        ctx["mouvements_recents"] = self.object.mouvements.order_by("-date_mouvement")[:15]
        ctx["bons_commande"]      = self.object.bons_commande.order_by("-date_creation")[:10]
        ctx["peut_administrer"]   = self.request.user.est_admin
        ctx["recommandation"]     = recommander_methode_approvisionnement(self.object)
        return ctx


class MatiereChoisirMethodeView(LoginRequiredMixin, View):
    """Étape 1 : Choix de la méthode d'approvisionnement."""
    template_name = "produits/matiere/choisir_methode.html"

    def get(self, request):
        # Réinitialiser la session de création si on arrive sur cette page
        if 'matiere_creation' in request.session:
            # On ne supprime que si on n'est pas en train de revenir en arrière
            if not request.GET.get('back'):
                del request.session['matiere_creation']
        
        from produits.abc_recommandation import recommander_methode_approvisionnement
        matiere_vide = MatierePremiere()
        recommandation = recommander_methode_approvisionnement(matiere_vide)
        
        ctx = {
            "recommandation": recommandation,
            "methode_recommandee_label": dict(MatierePremiere.MethodeApprovisionnement.choices).get(recommandation["methode_recommandee"], ""),
            "methode_alternative_label": dict(MatierePremiere.MethodeApprovisionnement.choices).get(recommandation["methode_alternative"], ""),
            "step": 1,
            "step_total": 3,
            "step_range": range(1, 4),
        }
        return render(request, self.template_name, ctx)

    def post(self, request):
        methode = request.POST.get("methode")
        if methode not in MatierePremiere.MethodeApprovisionnement.values:
            messages.error(request, "Méthode invalide.")
            return redirect("produits:matiere-choisir-methode")
        
        if 'matiere_creation' not in request.session:
            request.session['matiere_creation'] = {}
        
        request.session['matiere_creation']['methode'] = methode
        request.session.modified = True
        return redirect("produits:matiere-create-info")


class MatiereCreateInfoView(LoginRequiredMixin, View):
    """Étape 2 : Informations générales."""
    template_name = "produits/matiere/form_step1.html"

    def get(self, request):
        if 'matiere_creation' not in request.session or 'methode' not in request.session['matiere_creation']:
            return redirect("produits:matiere-choisir-methode")
        
        initial = request.session['matiere_creation'].get('info', {})
        form = MatierePremiereStep1Form(initial=initial)
        
        methode = request.session['matiere_creation']['methode']
        
        # Mapping des unités pour le JS
        unites = UnitesMesure.objects.all().values('id', 'nom', 'autorise_decimales')
        unites_json = json.dumps({u['id']: u['autorise_decimales'] for u in unites})
        
        ctx = {
            "form": form,
            "methode_choisie": methode,
            "methode_label": dict(MatierePremiere.MethodeApprovisionnement.choices).get(methode, ""),
            "step": 2,
            "step_total": 3,
            "unites_json": unites_json,
        }
        return render(request, self.template_name, ctx)

    def post(self, request):
        form = MatierePremiereStep1Form(request.POST)
        if form.is_valid():
            request.session['matiere_creation']['info'] = serialize_data(form.cleaned_data)
            request.session.modified = True
            return redirect("produits:matiere-create-params")
        
        methode = request.session['matiere_creation']['methode']
        ctx = {
            "form": form,
            "methode_choisie": methode,
            "methode_label": dict(MatierePremiere.MethodeApprovisionnement.choices).get(methode, ""),
            "step": 2,
            "step_total": 3,
            "step_range": range(1, 4),
        }
        return render(request, self.template_name, ctx)


class MatiereCreateParamsView(LoginRequiredMixin, View):
    """Étape 3 : Paramètres de méthode et création finale."""
    template_name = "produits/matiere/form_step2.html"

    def get(self, request):
        if 'matiere_creation' not in request.session or 'info' not in request.session['matiere_creation']:
            return redirect("produits:matiere-create-info")
        
        methode = request.session['matiere_creation']['methode']
        form_class = FORMULAIRES_PAR_METHODE.get(methode, MatierePointCommandeForm)
        
        initial = request.session['matiere_creation'].get('params', {})
        
        # Données pour le résumé
        info = request.session['matiere_creation']['info']
        unite_obj = None
        if info.get('unite'):
            unite_obj = UnitesMesure.objects.filter(pk=info['unite']).first()
        
        form = form_class(initial=initial, unite=unite_obj)
        
        # Mapping des unités pour le JS
        unites = UnitesMesure.objects.all().values('id', 'nom', 'autorise_decimales')
        unites_json = json.dumps({u['id']: u['autorise_decimales'] for u in unites})
        
        ctx = {
            "form": form,
            "methode_code": methode,
            "methode_label": dict(MatierePremiere.MethodeApprovisionnement.choices).get(methode, ""),
            "methode_config": PARAMS_PAR_METHODE.get(methode, {}),
            "info_resume": info,
            "step": 3,
            "step_total": 3,
            "step_range": range(1, 4),
            "is_creation": True,
            "unite_obj": unite_obj,
            "unites_json": unites_json,
        }
        return render(request, self.template_name, ctx)

    def post(self, request):
        methode = request.session['matiere_creation']['methode']
        form_class = FORMULAIRES_PAR_METHODE.get(methode, MatierePointCommandeForm)
        form = form_class(request.POST)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    info = request.session['matiere_creation']['info']
                    params = form.cleaned_data
                    
                    # Préparer les données pour le modèle
                    creation_data = {}
                    for k, v in info.items():
                        # Si c'est un ID de ForeignKey (unite, fournisseur_principal)
                        if k in ['unite', 'fournisseur_principal']:
                            creation_data[f"{k}_id"] = v
                        else:
                            creation_data[k] = v
                    
                    matiere = MatierePremiere(**creation_data)
                    matiere.methode_approvisionnement = methode
                    # Appliquer les paramètres de la méthode
                    for field, value in params.items():
                        setattr(matiere, field, value)
                    
                    matiere.save()
                    
                    log_action(
                        request,
                        JournalActivite.TypeAction.CREATION,
                        'MatierePremiere',
                        matiere.pk,
                        f"Création finale de la matière {matiere.nom} (Méthode: {methode})"
                    )
                    
                    if 'matiere_creation' in request.session:
                        del request.session['matiere_creation']
                    messages.success(request, f"Matière « {matiere.nom} » créée avec succès.")
                    return redirect(reverse("produits:matiere-detail", kwargs={"pk": matiere.pk}))
            except Exception as e:
                messages.error(request, f"Erreur lors de la création : {str(e)}")
        
        # En cas d'erreur de formulaire
        info = request.session['matiere_creation']['info']
        ctx = {
            "form": form,
            "methode_code": methode,
            "methode_label": dict(MatierePremiere.MethodeApprovisionnement.choices).get(methode, ""),
            "methode_config": PARAMS_PAR_METHODE.get(methode, {}),
            "info_resume": info,
            "step": 3,
            "step_total": 3,
            "is_creation": True,
        }
        return render(request, self.template_name, ctx)


class MatiereCreationAnnulerView(LoginRequiredMixin, View):
    """Annulation de la création : vide la session et redirige."""
    def get(self, request):
        if 'matiere_creation' in request.session:
            del request.session['matiere_creation']
        return redirect("produits:matiere-liste")


class MatiereCreerView(LoginRequiredMixin, View):
    """Redirection legacy pour garder la compatibilité des liens directs."""
    def get(self, request):
        return redirect("produits:matiere-choisir-methode")


# ============================================================
# PRODUITS FINIS
# ============================================================

class ProduitFiniListeView(LoginRequiredMixin, KanbanListMixin, ExportMixin, ListView):
    model               = ProduitFini
    template_name       = "produits/produit_fini/liste.html"
    kanban_template_name = "produits/produit_fini/kanban.html"
    context_object_name = "produits"
    paginate_by         = 25

    export_fields       = ['reference', 'nom', 'categorie', 'stock_actuel', 'unite__symbole', 'stock_minimum', 'statut']
    export_headers      = ['Référence', 'Nom', 'Catégorie', 'Stock Actuel', 'Unité', 'Stock Min', 'Statut']

    def get_queryset(self):
        qs = ProduitFini.objects.select_related("unite").annotate(
            calculated_statut=Case(
                When(stock_actuel__lte=0, then=Value('RUPTURE')),
                When(stock_actuel__lte=F('stock_minimum'), then=Value('CRITIQUE')),
                When(stock_maximum__gt=0, stock_actuel__lt=F('stock_maximum')*0.5, then=Value('ALERTE')),
                default=Value('NORMAL'),
                output_field=CharField(),
            )
        )
        
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(Q(nom__icontains=q) | Q(reference__icontains=q))
            
        categorie = self.request.GET.get("categorie")
        if categorie:
            qs = qs.filter(categorie=categorie)
            
        statut = self.request.GET.get("statut")
        if statut:
            qs = qs.filter(statut=statut)

        statut_stock = self.request.GET.get("statut_stock")
        if statut_stock:
            qs = qs.filter(calculated_statut=statut_stock)
            
        actif = self.request.GET.get("actif")
        if actif == "0":
            qs = qs.filter(actif=False)
        elif actif == "1":
            qs = qs.filter(actif=True)
            
        return qs.order_by("reference")

    def get(self, request, *args, **kwargs):
        export_type = request.GET.get('export')
        if export_type == 'csv':
            return self.render_to_csv(self.get_queryset(), filename_prefix="produits_finis")
        elif export_type == 'pdf':
            return self.render_to_pdf(self.get_queryset(), title="Liste des Produits Finis", filename_prefix="produits_finis")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["categories"] = ProduitFini.Categorie.choices
        ctx["statuts_choices"] = ProduitFini.Statut.choices
        ctx["statut_stock_choices"] = [
            ('RUPTURE', 'Rupture'),
            ('CRITIQUE', 'Critique'),
            ('ALERTE', 'Alerte'),
            ('NORMAL', 'Normal'),
        ]
        return ctx


class ProduitFiniDetailView(LoginRequiredMixin, DetailView):
    model               = ProduitFini
    template_name       = "produits/produit_fini/detail.html"
    context_object_name = "produit"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["mouvements_recents"] = self.object.mouvements.order_by("-date_mouvement")[:10]
        ctx["peut_administrer"]   = self.request.user.est_admin
        return ctx


class ProduitFiniCreerView(LoginRequiredMixin, UnitValidationMixin, CreateView):
    model         = ProduitFini
    form_class    = ProduitFiniForm
    template_name = "produits/produit_fini/form.html"
    success_url   = reverse_lazy("produits:produit-fini-liste")

    def form_valid(self, form):
        response = super().form_valid(form)
        log_action(
            self.request,
            JournalActivite.TypeAction.CREATION,
            'ProduitFini',
            self.object.pk,
            f"Création du produit fini {self.object.nom}"
        )
        messages.success(self.request, _("Produit fini créé avec succès."))
        return response


class ProduitFiniModifierView(LoginRequiredMixin, UnitValidationMixin, UpdateView):
    model         = ProduitFini
    form_class    = ProduitFiniForm
    template_name = "produits/produit_fini/form.html"

    def get_success_url(self):
        return reverse("produits:produit-fini-detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        response = super().form_valid(form)
        log_action(
            self.request,
            JournalActivite.TypeAction.MODIFICATION,
            'ProduitFini',
            self.object.pk,
            f"Modification du produit fini {self.object.nom}"
        )
        messages.success(self.request, _("Produit fini modifié avec succès."))
        return response


class ProduitFiniSupprimerView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model         = ProduitFini
    template_name = "produits/produit_fini/confirm_delete.html"
    success_url   = reverse_lazy("produits:produit-fini-liste")

    def test_func(self):
        return self.request.user.est_admin

    def delete(self, request, *args, **kwargs):
        # Désactivation au lieu de suppression physique si mouvements existants
        obj = self.get_object()
        if obj.mouvements.exists():
            obj.actif = False
            obj.save()
            log_action(
                request,
                JournalActivite.TypeAction.SUPPRESSION,
                'ProduitFini',
                obj.pk,
                f"Désactivation du produit fini {obj.nom} (mouvements existants)"
            )
            messages.warning(request, _("Le produit a été désactivé car il possède des mouvements de stock."))
            return redirect(self.success_url)
        
        log_action(
            request,
            JournalActivite.TypeAction.SUPPRESSION,
            'ProduitFini',
            obj.pk,
            f"Suppression physique du produit fini {obj.nom}"
        )
        messages.success(request, _("Produit fini supprimé."))
        return super().delete(request, *args, **kwargs)


@login_required
def export_produits_finis_csv(request):
    """Export CSV des produits finis."""
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="produits_finis.csv"'
    response.write('\ufeff')  # BOM for Excel
    
    writer = csv.writer(response, delimiter=";")
    writer.writerow(["Référence", "Nom", "Catégorie", "Statut", "Stock Actuel", "Unité", "Valeur Stock"])
    
    produits = ProduitFini.objects.filter(actif=True).select_related("unite")
    for p in produits:
        writer.writerow([
            p.reference, p.nom, p.get_categorie_display(), p.get_statut_display(),
            p.stock_actuel, p.unite.symbole if p.unite else "",
            float(p.valeur_stock)
        ])
    return response


# ============================================================
# NOMENCLATURES (BOM)
# ============================================================

class NomenclatureCreerView(LoginRequiredMixin, CreateView):
    model         = Nomenclature
    form_class    = NomenclatureForm
    template_name = "produits/nomenclature/form.html"

    def form_valid(self, form):
        produit = get_object_or_404(ProduitFini, pk=self.kwargs["produit_pk"])
        form.instance.produit_fini = produit
        messages.success(self.request, _("Nomenclature créée avec succès."))
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("produits:produit-fini-detail", kwargs={"pk": self.kwargs["produit_pk"]})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["produit"] = get_object_or_404(ProduitFini, pk=self.kwargs["produit_pk"])
        return ctx


class NomenclatureModifierView(LoginRequiredMixin, UpdateView):
    model         = Nomenclature
    form_class    = NomenclatureForm
    template_name = "produits/nomenclature/form.html"

    def get_success_url(self):
        return reverse("produits:produit-fini-detail", kwargs={"pk": self.object.produit_fini.pk})

    def form_valid(self, form):
        messages.success(self.request, _("Nomenclature modifiée avec succès."))
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["produit"] = self.object.produit_fini
        return ctx


class NomenclatureSupprimerView(LoginRequiredMixin, DeleteView):
    model = Nomenclature

    def get_success_url(self):
        return reverse("produits:produit-fini-detail", kwargs={"pk": self.object.produit_fini.pk})

    def delete(self, request, *args, **kwargs):
        messages.success(request, _("Nomenclature supprimée."))
        return super().delete(request, *args, **kwargs)


class LigneNomenclatureAjouterView(LoginRequiredMixin, CreateView):
    model         = LigneNomenclature
    form_class    = LigneNomenclatureForm
    template_name = "produits/nomenclature/ligne_form.html"

    def form_valid(self, form):
        nomenclature = get_object_or_404(Nomenclature, pk=self.kwargs["nomenclature_pk"])
        form.instance.nomenclature = nomenclature
        messages.success(self.request, _("Composant ajouté à la nomenclature."))
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("produits:produit-fini-detail", kwargs={"pk": self.object.nomenclature.produit_fini.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["nomenclature"] = get_object_or_404(Nomenclature, pk=self.kwargs["nomenclature_pk"])
        return ctx


class LigneNomenclatureModifierView(LoginRequiredMixin, UpdateView):
    model         = LigneNomenclature
    form_class    = LigneNomenclatureForm
    template_name = "produits/nomenclature/ligne_form.html"

    def get_success_url(self):
        return reverse("produits:produit-fini-detail", kwargs={"pk": self.object.nomenclature.produit_fini.pk})

    def form_valid(self, form):
        messages.success(self.request, _("Composant de nomenclature modifié."))
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["nomenclature"] = self.object.nomenclature
        return ctx


class LigneNomenclatureSupprimerView(LoginRequiredMixin, DeleteView):
    model = LigneNomenclature

    def get_success_url(self):
        return reverse("produits:produit-fini-detail", kwargs={"pk": self.object.nomenclature.produit_fini.pk})

    def delete(self, request, *args, **kwargs):
        messages.success(request, _("Composant supprimé de la nomenclature."))
        return super().delete(request, *args, **kwargs)


# ============================================================
# PARAMÈTRES PAR MÉTHODE (step 2)
# ============================================================

# ============================================================
# CONFIGURATION DES MÉTHODES — structure enrichie
# ============================================================

PARAMS_PAR_METHODE = {
    "POINT_COMMANDE": {
        # Champs éditables dans le formulaire step 2
        "fields": ["point_commande", "qec", "delai_livraison_jours"],
        # Champs affichés en lecture seule dans le résumé
        "readonly_fields": ["stock_actuel", "stock_securite"],
        "description": (
            "La commande est déclenchée automatiquement quand le stock actuel descend "
            "sous le point de commande (ROP). La quantité commandée est la QEC."
        ),
        "icon": "bi-graph-down-arrow",
        "couleur": "primary",
        "formulas": {
            "point_commande": "ROP = Consommation journalière moyenne × Délai livraison + Stock sécurité",
            "qec": "QEC = √(2 × Demande annuelle × Coût de commande / Coût de possession annuel unitaire)",
        },
        "labels": {
            "point_commande": "Point de commande — ROP",
            "qec": "QEC — Quantité économique de commande (facultatif)",
            "delai_livraison_jours": "Délai de livraison fournisseur (jours)",
        },
        "help_texts": {
            "point_commande": "Seuil de déclenchement : une proposition est générée quand stock actuel ≤ ROP.",
            "qec": "Si 0, la quantité proposée sera stock_maximum − stock_actuel.",
            "delai_livraison_jours": "Utilisé pour calculer la date de besoin estimée.",
        },
        "message_aide": None,
    },
    "REAPPRO_FIXE": {
        "fields": ["qec", "periode_reappro_jours", "delai_livraison_jours"],
        "readonly_fields": ["stock_actuel", "stock_securite"],
        "description": (
            "Une quantité fixe (Q = QEC) est commandée à chaque période T. "
            "Idéal pour les matières à délai de livraison stable et consommation prévisible."
        ),
        "icon": "bi-calendar-check",
        "couleur": "success",
        "formulas": {
            "qec": "Q fixe commandée à chaque déclenchement de la période T",
        },
        "labels": {
            "qec": "Quantité fixe commandée (QEC)",
            "periode_reappro_jours": "Période de réapprovisionnement T (jours)",
            "delai_livraison_jours": "Délai de livraison fournisseur (jours)",
        },
        "help_texts": {
            "qec": "Quantité commandée à chaque cycle. Si 0, sera calculée automatiquement.",
            "periode_reappro_jours": "Intervalle entre deux commandes. Doit être > 0.",
            "delai_livraison_jours": "Utilisé pour éviter les ruptures entre commande et réception.",
        },
        "message_aide": None,
    },
    "RECOMPLETEMENT": {
        "fields": ["stock_maximum", "periode_reappro_jours", "delai_livraison_jours"],
        "readonly_fields": ["stock_actuel", "stock_securite", "stock_minimum"],
        "description": (
            "À chaque révision périodique T, on commande la différence entre le niveau cible S "
            "(stock maximum) et le stock actuel. Méthode de révision périodique."
        ),
        "icon": "bi-arrow-repeat",
        "couleur": "info",
        "formulas": {
            "stock_maximum": "Quantité à commander = S (stock max) − stock actuel − commandes en cours",
        },
        "labels": {
            "stock_maximum": "Niveau cible S (stock maximum)",
            "periode_reappro_jours": "Période de révision T (jours)",
            "delai_livraison_jours": "Délai de livraison fournisseur (jours)",
        },
        "help_texts": {
            "stock_maximum": "Niveau auquel on recompète le stock à chaque révision. Doit être > 0.",
            "periode_reappro_jours": "Intervalle entre deux révisions. Doit être > 0.",
            "delai_livraison_jours": "Utilisé pour ajuster la date de livraison prévue.",
        },
        "message_aide": None,
    },
    "MRP": {
        "fields": ["taux_rebut", "delai_livraison_jours", "periode_reappro_jours"],
        "readonly_fields": ["stock_actuel"],
        "description": (
            "Les besoins sont calculés par décomposition du plan de production. "
            "Configurez uniquement le taux de rebut et les délais."
        ),
        "icon": "bi-diagram-3",
        "couleur": "warning",
        "formulas": {
            "taux_rebut": "Besoin brut ajusté = Besoin brut ÷ (1 − taux_rebut)",
        },
        "labels": {
            "taux_rebut": "Taux de rebut / perte (%)",
            "delai_livraison_jours": "Délai de livraison fournisseur (jours)",
            "periode_reappro_jours": "Période de regroupement des besoins (jours)",
            "lot_minimum": "Lot minimum",
            "multiple_lot": "Multiple de lot",
        },
        "help_texts": {
            "taux_rebut": "Proportion de matière perdue en production. Saisir 0 si aucune perte.",
            "delai_livraison_jours": "Délai moyen entre la commande et la réception (jalonnement MRP).",
            "periode_reappro_jours": "Nombre de jours pendant lesquels les besoins MRP proches sont regroupés dans une seule proposition.",
            "lot_minimum": "Quantité minimale pour toute proposition de commande.",
            "multiple_lot": "La quantité proposée sera toujours un multiple de cette valeur.",
        },
        "message_aide": (
            "En méthode MRP, les besoins sont calculés à partir des produits finis à produire, "
            "des nomenclatures, du stock disponible, des réceptions planifiées et des délais "
            "d'approvisionnement. Les quantités proposées sont générées automatiquement par le planificateur."
        ),
    },
}


class MatiereParametresMethodeView(LoginRequiredMixin, UpdateView):
    """
    Étape 2 : paramètres spécifiques à la méthode d'approvisionnement.
    Utilise le formulaire dédié à la méthode via get_formulaire_methode().
    """
    model         = MatierePremiere
    template_name = "produits/matiere/form_step2.html"

    def get_object(self, queryset=None):
        if not hasattr(self, "_object"):
            self._object = super().get_object(queryset)
        return self._object

    def get_form_class(self):
        methode = self.get_object().methode_approvisionnement
        return FORMULAIRES_PAR_METHODE.get(methode, FORMULAIRES_PAR_METHODE["POINT_COMMANDE"])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        methode = self.object.methode_approvisionnement
        cfg = PARAMS_PAR_METHODE.get(methode, {})
        ctx["methode_config"] = cfg
        ctx["methode_label"]  = self.object.get_methode_approvisionnement_display()
        ctx["methode_code"]   = methode
        ctx["step"]           = 2
        ctx["step_total"]     = 2
        ctx["step_range"]     = range(1, 3)
        return ctx

    def form_valid(self, form):
        form.save()
        log_action(
            self.request,
            JournalActivite.TypeAction.MODIFICATION,
            'MatierePremiere',
            self.object.pk,
            f"Configuration (Étape 2) de la matière {self.object.nom}"
        )
        messages.success(
            self.request,
            f"Matière « {self.object.nom} » créée et configurée avec succès."
        )
        return redirect(reverse("produits:matiere-detail", kwargs={"pk": self.object.pk}))


class MatiereModifierView(LoginRequiredMixin, UnitValidationMixin, UpdateView):
    """
    Modification complète d'une matière.
    Le template form.html affiche dynamiquement les champs de la carte
    Approvisionnement selon la méthode choisie (JavaScript).
    """
    model         = MatierePremiere
    template_name = "produits/matiere/form.html"
    form_class    = MatierePremiereForm

    def get_form_kwargs(self):
        """S'assure que l'instance est bien passée au formulaire."""
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.object
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Passe la config de toutes les méthodes au template pour le JS dynamique
        ctx["params_par_methode"] = PARAMS_PAR_METHODE
        ctx["methode_actuelle"]   = self.object.methode_approvisionnement
        ctx["is_update"]          = True
        return ctx

    def get_success_url(self):
        log_action(
            self.request,
            JournalActivite.TypeAction.MODIFICATION,
            'MatierePremiere',
            self.object.pk,
            f"Modification de la matière {self.object.nom}"
        )
        messages.success(self.request, _("Matière première mise à jour."))
        return reverse_lazy("produits:matiere-detail", kwargs={"pk": self.object.pk})


# ============================================================
# FOURNISSEURS
# ============================================================

class FournisseurListeView(LoginRequiredMixin, KanbanListMixin, ExportMixin, ListView):
    model               = Fournisseur
    template_name       = "produits/fournisseur/liste.html"
    kanban_template_name = "produits/fournisseur/kanban.html"
    context_object_name = "fournisseurs"
    paginate_by         = 25
    export_fields       = ['nom', 'contact', 'email', 'telephone', 'ville', 'statut']
    export_headers      = ['Raison Sociale', 'Contact', 'Email', 'Téléphone', 'Ville', 'Statut']

    def get_queryset(self):
        qs = Fournisseur.objects.all()
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(Q(nom__icontains=q) | Q(ville__icontains=q) | Q(pays__icontains=q))
            
        statut = self.request.GET.get("statut")
        if statut:
            qs = qs.filter(statut=statut)
            
        actif = self.request.GET.get("actif")
        if actif == "0":
            qs = qs.filter(actif=False)
        elif actif == "1":
            qs = qs.filter(actif=True)
            
        return qs.order_by("nom")

    def get(self, request, *args, **kwargs):
        export_type = request.GET.get('export')
        if export_type == 'csv':
            return self.render_to_csv(self.get_queryset(), filename_prefix="fournisseurs")
        elif export_type == 'pdf':
            return self.render_to_pdf(self.get_queryset(), title="Répertoire des Fournisseurs", filename_prefix="fournisseurs")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["statut_choices"] = Fournisseur.Statut.choices
        return ctx


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
            "unite_id":      m.unite.id if m.unite else None,
            "unite":         m.unite.symbole if m.unite else "",
            "autorise_decimales": m.unite.autorise_decimales if m.unite else True,
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
        log_action(
            self.request,
            JournalActivite.TypeAction.SUPPRESSION,
            'MatierePremiere',
            self.object.pk,
            f"Suppression de la matière {self.object.nom}"
        )
        messages.success(self.request, f"Matière « {self.object.nom} » supprimée.")
        return super().form_valid(form)
