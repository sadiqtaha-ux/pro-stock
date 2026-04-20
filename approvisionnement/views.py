"""approvisionnement/views.py"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView, View
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db.models import Q, Sum, F
from decimal import Decimal

from .models import BonCommande, PlanMRP, PropositionCommande
from produits.models import MatierePremiere, Fournisseur
from .planificateur import lancer_planification


class ApproDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "approvisionnement/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        # ── KPIs ──────────────────────────────────────────────
        ctx["commandes_en_cours"] = BonCommande.objects.filter(
            statut__in=[BonCommande.Statut.BROUILLON, BonCommande.Statut.ENVOYE]
        ).count()

        ctx["nb_ruptures"] = MatierePremiere.objects.filter(
            actif=True, stock_actuel__lte=0
        ).count()

        ctx["nb_alertes"] = MatierePremiere.objects.filter(
            actif=True,
            stock_actuel__gt=0,
            stock_actuel__lte=F("stock_minimum")
        ).count()

        ctx["valeur_engagee"] = BonCommande.objects.filter(
            statut__in=[BonCommande.Statut.ENVOYE, BonCommande.Statut.CONFIRME]
        ).aggregate(total=Sum("montant_total"))["total"] or 0

        ctx["total_produits"] = MatierePremiere.objects.filter(actif=True).count()

        # ── Matières par méthode (pour les onglets) ───────────
        base_qs = MatierePremiere.objects.filter(
            actif=True
        ).select_related("unite", "fournisseur_principal").order_by("stock_actuel")

        ctx["matieres_toutes"]         = base_qs
        ctx["matieres_point_commande"] = base_qs.filter(methode_approvisionnement="POINT_COMMANDE")
        ctx["matieres_reappro_fixe"]   = base_qs.filter(methode_approvisionnement="REAPPRO_FIXE")
        ctx["matieres_recompletement"] = base_qs.filter(methode_approvisionnement="RECOMPLETEMENT")
        ctx["matieres_mrp"]            = base_qs.filter(methode_approvisionnement="MRP")

        # ── Dernières commandes ───────────────────────────────
        ctx["dernieres_commandes"] = BonCommande.objects.select_related(
            "matiere", "fournisseur", "matiere__unite"
        ).order_by("-date_creation")[:8]

        return ctx


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
        methode = self.request.GET.get("methode")
        if methode:
            qs = qs.filter(methode_declenchement=methode)
        fournisseur_id = self.request.GET.get("fournisseur")
        if fournisseur_id:
            qs = qs.filter(fournisseur_id=fournisseur_id)
        date_from = self.request.GET.get("date_from")
        if date_from:
            qs = qs.filter(date_creation__date__gte=date_from)
        date_to = self.request.GET.get("date_to")
        if date_to:
            qs = qs.filter(date_creation__date__lte=date_to)
        return qs.order_by("-date_creation")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["statuts"] = BonCommande.Statut.choices
        ctx["methodes_choices"] = BonCommande.MethodeDeclenchement.choices
        ctx["fournisseurs"] = Fournisseur.objects.filter(actif=True).order_by("nom")
        ctx["montant_total_en_cours"] = BonCommande.objects.filter(
            statut__in=[BonCommande.Statut.ENVOYE, BonCommande.Statut.CONFIRME]
        ).aggregate(total=Sum("montant_total"))["total"] or 0
        # Compte les filtres actifs (hors pagination)
        ctx["active_filters_count"] = sum(
            1 for k, v in self.request.GET.items()
            if k != "page" and v
        )
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
class SuggestionListeView(LoginRequiredMixin, TemplateView):
    template_name = "approvisionnement/suggestions/liste.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["suggestions"] = []
        ctx["nb_urgentes"] = 0
        ctx["statuts"] = [("NOUVELLE", "Nouvelle"), ("TRANSFORMEE", "Transformée")]
        ctx["methodes"] = [
            ("POINT_COMMANDE", "Point de commande"),
            ("REAPPRO_FIXE", "Réappro fixe"),
            ("RECOMPLETEMENT", "Recomplètement"),
            ("MRP", "MRP"),
        ]
        return ctx


# ============================================================
# VUE KANBAN DES BONS DE COMMANDE
# ============================================================

class BonCommandeKanbanView(LoginRequiredMixin, TemplateView):
    template_name = "approvisionnement/commande/kanban.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs = BonCommande.objects.select_related("matiere", "fournisseur", "cree_par")
        colonnes = [
            ("BROUILLON", "Brouillons",  "secondary", "bi-pencil"),
            ("ENVOYE",    "Envoyés",      "primary",   "bi-send"),
            ("CONFIRME",  "Confirmés",    "info",      "bi-check2-circle"),
            ("RECU",      "Reçus",         "success",   "bi-box-seam"),
            ("ANNULE",    "Annulés",      "danger",    "bi-x-circle"),
        ]
        ctx["colonnes"] = [
            {
                "statut":    s,
                "label":     l,
                "color":     c,
                "icon":      ic,
                "commandes": qs.filter(statut=s),
            }
            for s, l, c, ic in colonnes
        ]
        return ctx


# ============================================================
# BONS DE COMMANDE — FORMULAIRE MULTI-ÉTAPES
# ============================================================

from django.views import View
from django.shortcuts import render


class BonCommandeStep1View(LoginRequiredMixin, View):
    """Étape 1 : choisir la matière et la méthode de déclenchement."""
    template_name = "approvisionnement/commande/form_step1.html"

    def get(self, request):
        matieres = MatierePremiere.objects.filter(
            actif=True
        ).select_related("unite", "fournisseur_principal").order_by("reference")

        matiere_id = request.GET.get("matiere")
        matiere_preselectionnee = None
        if matiere_id:
            matiere_preselectionnee = MatierePremiere.objects.filter(
                pk=matiere_id
            ).select_related("unite", "fournisseur_principal").first()

        return render(request, self.template_name, {
            "matieres":               matieres,
            "methodes":               BonCommande.MethodeDeclenchement.choices,
            "matiere_preselectionnee": matiere_preselectionnee,
            "step":                   1,
            "step_total":             2,
            "step_range":             range(1, 3),
        })

    def post(self, request):
        from django.urls import reverse
        matiere_id = request.POST.get("matiere")
        methode    = request.POST.get("methode_declenchement")

        if not matiere_id or not methode:
            messages.error(request, "Veuillez sélectionner une matière et une méthode.")
            return redirect("approvisionnement:commande-step1")

        return redirect(
            reverse("approvisionnement:commande-step2") +
            f"?matiere={matiere_id}&methode={methode}"
        )


class BonCommandeStep2View(LoginRequiredMixin, View):
    """Étape 2 : saisie des paramètres pré-remplis selon la méthode."""
    template_name = "approvisionnement/commande/form_step2.html"

    def _get_suggestion(self, matiere, methode):
        stock  = float(matiere.stock_actuel)
        s_max  = float(matiere.stock_maximum)
        s_min  = float(matiere.stock_minimum)
        qec    = float(matiere.qec)
        pc     = float(matiere.point_commande)

        if methode == "POINT_COMMANDE":
            quantite_suggeree = qec if qec > 0 else max(0, s_max - stock)
            note = (f"Stock actuel ({stock}) ≤ Point de commande ({pc}). "
                    f"Quantité économique de commande : {qec}")
        elif methode == "REAPPRO_FIXE":
            quantite_suggeree = qec if qec > 0 else max(0, s_max - stock)
            note = f"Quantité fixe paramétrée (QEC) : {qec}"
        elif methode == "RECOMPLETEMENT":
            quantite_suggeree = max(0, s_max - stock)
            note = (f"Recomplètement jusqu'au niveau cible S = {s_max}. "
                    f"Stock actuel = {stock}. Quantité = S − stock = {quantite_suggeree:.3f}")
        elif methode == "MRP":
            quantite_suggeree = 0
            note = "Quantité calculée par le Plan MRP."
        else:
            quantite_suggeree = max(0, s_max - stock)
            note = "Quantité saisie manuellement."

        return {
            "quantite_suggeree": round(quantite_suggeree, 4),
            "note_calcul":       note,
        }

    def get(self, request):
        from django.urls import reverse
        matiere_id = request.GET.get("matiere")
        methode    = request.GET.get("methode")

        if not matiere_id or not methode:
            return redirect("approvisionnement:commande-step1")

        matiere = get_object_or_404(
            MatierePremiere.objects.select_related("unite", "fournisseur_principal"),
            pk=matiere_id, actif=True
        )
        suggestion    = self._get_suggestion(matiere, methode)
        fournisseurs  = Fournisseur.objects.filter(actif=True).order_by("nom")
        methode_label = dict(BonCommande.MethodeDeclenchement.choices).get(methode, methode)

        alerte_niveau = "normal"
        if matiere.est_en_rupture:
            alerte_niveau = "rupture"
        elif matiere.est_en_alerte:
            alerte_niveau = "alerte"

        import datetime
        today = datetime.date.today().isoformat()

        return render(request, self.template_name, {
            "matiere":       matiere,
            "methode":       methode,
            "methode_label": methode_label,
            "suggestion":    suggestion,
            "fournisseurs":  fournisseurs,
            "statuts":       BonCommande.Statut.choices,
            "alerte_niveau": alerte_niveau,
            "today":         today,
            "step":          2,
            "step_total":    2,
            "step_range":    range(1, 3),
        })

    def post(self, request):
        from django.urls import reverse
        matiere_id  = request.POST.get("matiere_id")
        methode     = request.POST.get("methode_declenchement")
        matiere     = get_object_or_404(MatierePremiere, pk=matiere_id)
        fournisseur = get_object_or_404(Fournisseur, pk=request.POST.get("fournisseur"))
        try:
            commande = BonCommande.objects.create(
                matiere               = matiere,
                fournisseur           = fournisseur,
                quantite_commandee    = request.POST.get("quantite_commandee"),
                prix_unitaire         = request.POST.get("prix_unitaire") or 0,
                methode_declenchement = methode,
                statut                = request.POST.get("statut", "BROUILLON"),
                date_reception_prevue = request.POST.get("date_reception_prevue") or None,
                notes                 = request.POST.get("notes", ""),
                cree_par              = request.user,
            )
            messages.success(request, f"Bon de commande {commande.reference} créé avec succès.")
            return redirect(reverse("approvisionnement:commande-detail", kwargs={"pk": commande.pk}))
        except Exception as e:
            messages.error(request, f"Erreur lors de la création : {e}")
            return redirect("approvisionnement:commande-step1")


# ============================================================
# PLANIFICATEUR
# ============================================================

class PlanificateurView(LoginRequiredMixin, TemplateView):
    """
    Vue principale du planificateur.
    GET  → affiche les propositions PROPOSÉES.
    POST → lance le calcul via lancer_planification().
    """
    template_name = "approvisionnement/planificateur/index.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        ctx["propositions"] = PropositionCommande.objects.select_related(
            "matiere", "matiere__unite", "matiere__fournisseur_principal"
        ).filter(
            statut=PropositionCommande.Statut.PROPOSEE
        ).order_by("-urgence", "date_besoin")

        ctx["nb_urgentes"]   = ctx["propositions"].filter(urgence=True).count()
        ctx["nb_normales"]   = ctx["propositions"].filter(urgence=False).count()
        ctx["nb_converties"] = PropositionCommande.objects.filter(
            statut=PropositionCommande.Statut.CONVERTIE
        ).count()
        ctx["nb_rejetees"]   = PropositionCommande.objects.filter(
            statut=PropositionCommande.Statut.REJETEE
        ).count()
        ctx["fournisseurs_actifs"] = Fournisseur.objects.filter(actif=True).order_by("nom")

        return ctx

    def post(self, request, *args, **kwargs):
        force   = request.POST.get("force") == "1"
        results = lancer_planification(force=force)

        nb_err = len(results["erreurs"])
        if nb_err:
            messages.warning(
                request,
                f"{results['creees']} proposition(s) créée(s), "
                f"{results['ignorees']} ignorée(s), "
                f"{nb_err} erreur(s) : " + " | ".join(results["erreurs"])
            )
        else:
            messages.success(
                request,
                f"Planification terminée : {results['creees']} nouvelle(s) "
                f"proposition(s), {results['ignorees']} ignorée(s)."
            )
        return redirect("approvisionnement:planificateur")


class PropositionValiderView(LoginRequiredMixin, View):
    """
    Valider une proposition : crée un BonCommande, marque la proposition CONVERTIE.
    POST params : quantite_validee, fournisseur (pk), date_reception_prevue, note_acheteur.
    """
    def post(self, request, pk):
        proposition = get_object_or_404(
            PropositionCommande, pk=pk, statut=PropositionCommande.Statut.PROPOSEE
        )
        matiere = proposition.matiere

        # Fournisseur
        fournisseur_id = request.POST.get("fournisseur")
        if fournisseur_id:
            fournisseur = get_object_or_404(Fournisseur, pk=fournisseur_id)
        elif matiere.fournisseur_principal:
            fournisseur = matiere.fournisseur_principal
        else:
            messages.error(request, "Aucun fournisseur défini pour cette matière.")
            return redirect("approvisionnement:planificateur")

        # Quantité
        quantite_str = request.POST.get("quantite_validee", "").strip()
        try:
            quantite = Decimal(quantite_str) if quantite_str else proposition.quantite_proposee
        except Exception:
            quantite = proposition.quantite_proposee

        date_reception = request.POST.get("date_reception_prevue") or None

        # Créer le BonCommande
        bon = BonCommande.objects.create(
            matiere               = matiere,
            fournisseur           = fournisseur,
            quantite_commandee    = quantite,
            prix_unitaire         = matiere.prix_unitaire,
            methode_declenchement = proposition.methode,
            statut                = BonCommande.Statut.BROUILLON,
            date_reception_prevue = date_reception,
            notes                 = (
                "Généré par le planificateur. "
                + proposition.detail_calcul.get("regle", "")
            ),
            cree_par              = request.user,
        )

        # Mettre à jour la proposition
        proposition.quantite_validee = quantite
        proposition.statut           = PropositionCommande.Statut.CONVERTIE
        proposition.bon_commande     = bon
        proposition.note_acheteur    = request.POST.get("note_acheteur", "")
        proposition.save()

        messages.success(
            request,
            f"Bon de commande {bon.reference} créé. "
            f"Vous pouvez maintenant le modifier et l'envoyer."
        )
        return redirect("approvisionnement:commande-detail", pk=bon.pk)


class PropositionRejeterView(LoginRequiredMixin, View):
    """Rejeter une proposition avec une note obligatoire."""
    def post(self, request, pk):
        proposition = get_object_or_404(
            PropositionCommande, pk=pk, statut=PropositionCommande.Statut.PROPOSEE
        )
        proposition.statut        = PropositionCommande.Statut.REJETEE
        proposition.note_acheteur = request.POST.get("note_rejet", "")
        proposition.save()
        messages.info(request, "Proposition rejetée.")
        return redirect("approvisionnement:planificateur")
