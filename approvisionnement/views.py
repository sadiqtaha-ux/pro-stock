"""approvisionnement/views.py"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView, View
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db.models import Q, Sum, F, Count
from decimal import Decimal

from core.mixins import KanbanListMixin, ExportMixin
from core.models import JournalActivite
from core.utils import log_action

from .models import BonCommande, PlanMRP, PropositionCommande
from produits.models import MatierePremiere, Fournisseur, ProduitFini
from produits.views import UnitValidationMixin
from .planificateur import lancer_planification
from .services import ExplosionBesoinsMRP
import json


# ============================================================
# SIMULATEUR MRP (Explosion de Nomenclature)
# ============================================================

class SimulateurMRPView(LoginRequiredMixin, TemplateView):
    """
    Vue visuelle pour le calcul MRP basé sur un produit fini et une quantité.
    """
    template_name = "approvisionnement/mrp/simulateur.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        produit_id = self.request.GET.get("produit")
        quantite   = self.request.GET.get("quantite", 1)
        
        ctx["produits_finis"] = ProduitFini.objects.filter(actif=True).order_by("nom")
        
        if produit_id:
            produit = get_object_or_404(ProduitFini, pk=produit_id)
            ctx["produit_selectionne"] = produit
            ctx["quantite_cible"]      = float(quantite)
            
            # Explosion des besoins
            ctx["resultats"] = ExplosionBesoinsMRP.calculer(produit, quantite)
            
            # Statistiques globales
            ctx["nb_bloquants"] = sum(1 for r in ctx["resultats"] if r["bloquant"])
            ctx["nb_a_commander"] = sum(1 for r in ctx["resultats"] if r["quantite_proposee"] > 0)
            ctx["nb_mrp"] = sum(1 for r in ctx["resultats"] if r["statut"] != "NON_MRP")
            ctx["nb_non_mrp"] = sum(1 for r in ctx["resultats"] if r["statut"] == "NON_MRP")
            
        return ctx

    def post(self, request, *args, **kwargs):
        """
        Action pour transformer les besoins en propositions de commande.
        """
        produit_id = request.POST.get("produit_id")
        quantites  = request.POST.getlist("quantites_prop")
        matieres   = request.POST.getlist("matiere_ids")
        
        compteur = 0
        for m_id, qte in zip(matieres, quantites):
            qte_val = float(qte or 0)
            if qte_val > 0:
                m = get_object_or_404(MatierePremiere, pk=m_id)
                PropositionCommande.objects.create(
                    matiere=m,
                    methode="MRP",
                    quantite_proposee=qte_val,
                    statut=PropositionCommande.Statut.EN_ATTENTE,
                    urgence=(m.stock_actuel <= 0),
                    detail_calcul={
                        "origine": "SIMULATEUR_MRP",
                        "produit_fini": produit_id,
                        "regle": f"Généré depuis simulateur MRP pour PF ID {produit_id}"
                    }
                )
                log_action(
                    request,
                    JournalActivite.TypeAction.CREATION,
                    'PropositionCommande',
                    None,
                    f"Proposition MRP créée via simulateur pour {m.nom}"
                )
                compteur += 1
        
        if compteur > 0:
            messages.success(request, f"{compteur} propositions de commande ont été créées.")
            return redirect("approvisionnement:commandes-a-valider")
        
        messages.info(request, "Aucune proposition créée.")
        return redirect(request.path + f"?produit={produit_id}")


class ApproDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "approvisionnement/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        # ── KPIs ──────────────────────────────────────────────
        ctx["commandes_en_cours"] = PropositionCommande.objects.filter(
            statut=PropositionCommande.Statut.EN_ATTENTE
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


class BonCommandeListeView(LoginRequiredMixin, KanbanListMixin, ExportMixin, ListView):
    model               = BonCommande
    template_name       = "approvisionnement/commande/liste.html"
    kanban_template_name = "approvisionnement/commande/kanban.html"
    context_object_name = "commandes"
    paginate_by         = 25
    export_fields       = ['reference', 'matiere__nom', 'fournisseur__nom', 'quantite_commandee', 'prix_unitaire', 'montant_total', 'statut', 'date_creation']
    export_headers      = ['Référence', 'Matière', 'Fournisseur', 'Qté Commandée', 'P.U.', 'Montant Total', 'Statut', 'Date Création']

    def get_queryset(self):
        qs = BonCommande.objects.select_related("matiere", "fournisseur", "cree_par", "matiere__unite")
        
        # Filtres de base
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
            
        # Filtres de dates
        date_from = self.request.GET.get("date_from")
        if date_from:
            qs = qs.filter(date_creation__date__gte=date_from)
            
        date_to = self.request.GET.get("date_to")
        if date_to:
            qs = qs.filter(date_creation__date__lte=date_to)
            
        # Filtres spécifiques
        retard = self.request.GET.get("retard")
        if retard == "1":
            from django.utils import timezone
            qs = qs.exclude(statut__in=[BonCommande.Statut.RECU, BonCommande.Statut.ANNULE]).filter(
                date_reception_prevue__lt=timezone.now().date()
            )
            
        return qs.order_by("-date_creation")

    def get(self, request, *args, **kwargs):
        export_type = request.GET.get('export')
        if export_type == 'csv':
            return self.render_to_csv(self.get_queryset(), filename_prefix="commandes")
        elif export_type == 'pdf':
            return self.render_to_pdf(self.get_queryset(), title="Registre des Commandes d'Achat", filename_prefix="commandes")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["statuts_choices"] = BonCommande.Statut.choices
        ctx["methodes_choices"] = BonCommande.MethodeDeclenchement.choices
        ctx["fournisseurs"] = Fournisseur.objects.filter(actif=True).order_by("nom")
        ctx["montant_total_en_cours"] = BonCommande.objects.filter(
            statut__in=[BonCommande.Statut.ENVOYE, BonCommande.Statut.CONFIRME]
        ).aggregate(total=Sum("montant_total"))["total"] or 0
        return ctx


class BonCommandeDetailView(LoginRequiredMixin, DetailView):
    model               = BonCommande
    template_name       = "approvisionnement/commande/detail.html"
    context_object_name = "commande"


class BonCommandeModifierView(LoginRequiredMixin, UnitValidationMixin, UpdateView):
    model         = BonCommande
    template_name = "approvisionnement/commande/form.html"
    fields        = [
        "matiere", "fournisseur", "quantite_commandee", "prix_unitaire",
        "methode_declenchement", "statut",
        "date_reception_prevue", "date_reception_reelle", "notes"
    ]

    def form_valid(self, form):
        response = super().form_valid(form)
        log_action(
            self.request,
            JournalActivite.TypeAction.MODIFICATION,
            'BonCommande',
            self.object.pk,
            f"Modification du bon de commande {self.object.reference}"
        )
        messages.success(self.request, _("Bon de commande mis à jour."))
        return response

    def get_success_url(self):
        return reverse_lazy("approvisionnement:commande-detail", kwargs={"pk": self.object.pk})


class PlanMRPListeView(LoginRequiredMixin, ListView):
    model               = PlanMRP
    template_name       = "approvisionnement/mrp/liste.html"
    context_object_name = "plans"
    paginate_by         = 30

    def get_queryset(self):
        return PlanMRP.objects.select_related("matiere").order_by("-periode")


class PlanMRPCreerView(LoginRequiredMixin, UnitValidationMixin, CreateView):
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


class PlanificateurView(LoginRequiredMixin, KanbanListMixin, ExportMixin, ListView):
    """
    Vue principale du planificateur.
    GET  → affiche les propositions (En attente, Validées, Rejetées, Converties).
    POST → lance le calcul via PlanificateurService.
    """
    model               = PropositionCommande
    template_name       = "approvisionnement/planificateur/index.html"
    kanban_template_name = "approvisionnement/planificateur/kanban.html"
    context_object_name = "propositions"
    paginate_by         = 25
    export_fields       = ['matiere__nom', 'methode', 'quantite_proposee', 'quantite_validee', 'urgence', 'statut', 'date_besoin']
    export_headers      = ['Matière', 'Méthode', 'Qté Proposée', 'Qté Validée', 'Urgent', 'Statut', 'Date Besoin']

    def get_queryset(self):
        qs = PropositionCommande.objects.select_related(
            "matiere", "matiere__unite", "fournisseur"
        )
        
        # Filtres
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(Q(matiere__nom__icontains=q) | Q(matiere__reference__icontains=q))
            
        statut = self.request.GET.get("statut")
        if statut:
            qs = qs.filter(statut=statut)
        else:
            if self.request.GET.get('view') != 'kanban':
                qs = qs.filter(statut=PropositionCommande.Statut.EN_ATTENTE)
                
        methode = self.request.GET.get("methode")
        if methode:
            qs = qs.filter(methode=methode)
            
        urgence = self.request.GET.get("urgence")
        if urgence == "1":
            qs = qs.filter(urgence=True)
            
        fournisseur = self.request.GET.get("fournisseur")
        if fournisseur:
            qs = qs.filter(fournisseur_id=fournisseur)
            
        return qs.order_by("-urgence", "date_besoin")

    def get(self, request, *args, **kwargs):
        export_type = request.GET.get('export')
        if export_type == 'csv':
            return self.render_to_csv(self.get_queryset(), filename_prefix="propositions_appro")
        elif export_type == 'pdf':
            return self.render_to_pdf(self.get_queryset(), title="Propositions d'Approvisionnement", filename_prefix="propositions_appro")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["fournisseurs_actifs"] = Fournisseur.objects.filter(actif=True).order_by("nom")
        ctx["statuts_choices"] = PropositionCommande.Statut.choices
        ctx["methodes_choices"] = [
            ("POINT_COMMANDE", "Point de commande"),
            ("REAPPRO_FIXE", "Réappro fixe"),
            ("RECOMPLETEMENT", "Recomplètement"),
            ("MRP", "MRP"),
        ]
        
        all_props = PropositionCommande.objects.all()
        ctx["nb_proposees"]  = all_props.filter(statut=PropositionCommande.Statut.EN_ATTENTE).count()
        ctx["nb_urgentes"]   = all_props.filter(statut=PropositionCommande.Statut.EN_ATTENTE, urgence=True).count()
        ctx["nb_converties"] = all_props.filter(statut=PropositionCommande.Statut.CONVERTIE).count()
        
        return ctx

    def post(self, request, *args, **kwargs):
        from .services import PlanificateurService
        results = PlanificateurService.run_planificateur(utilisateur=request.user)

        nb_err = len(results["errors"])
        if nb_err:
            messages.warning(
                request,
                f"{results['created']} proposition(s) créée(s), "
                f"{results['updated']} mise(s) à jour, "
                f"{results['skipped']} ignorée(s), "
                f"{nb_err} erreur(s) : " + " | ".join(results["errors"])
            )
        else:
            messages.success(
                request,
                f"Planification terminée : {results['created']} nouvelle(s) "
                f"proposition(s), {results['updated']} mise(s) à jour, {results['skipped']} ignorée(s)."
            )
        
        log_action(
            request,
            JournalActivite.TypeAction.CREATION,
            'Planificateur',
            None,
            f"Lancement du planificateur : {results['created']} propositions créées"
        )
        return redirect("approvisionnement:commandes-a-valider")


class PropositionValiderView(LoginRequiredMixin, View):
    """
    Valider une proposition : crée un BonCommande, marque la proposition CONVERTIE.
    POST params : quantite_validee, fournisseur (pk), date_reception_prevue, note_acheteur.
    """
    def post(self, request, pk):
        proposition = get_object_or_404(
            PropositionCommande, pk=pk, statut=PropositionCommande.Statut.EN_ATTENTE
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
            return redirect("approvisionnement:commandes-a-valider")

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
        log_action(
            request,
            JournalActivite.TypeAction.VALIDATION,
            'PropositionCommande',
            proposition.pk,
            f"Validation de la proposition pour {matiere.nom} -> BC {bon.reference}"
        )
        return redirect("approvisionnement:commande-detail", pk=bon.pk)


class PropositionRejeterView(LoginRequiredMixin, View):
    """Rejeter une proposition avec une note obligatoire."""
    def post(self, request, pk):
        proposition = get_object_or_404(
            PropositionCommande, pk=pk, statut=PropositionCommande.Statut.EN_ATTENTE
        )
        proposition.statut        = PropositionCommande.Statut.REJETEE
        proposition.note_acheteur = request.POST.get("note_rejet", "")
        proposition.save()
        log_action(
            request,
            JournalActivite.TypeAction.REJET,
            'PropositionCommande',
            proposition.pk,
            f"Rejet de la proposition pour {proposition.matiere.nom}. Motif: {proposition.note_acheteur}"
        )
        messages.info(request, "Proposition rejetée.")
        return redirect("approvisionnement:commandes-a-valider")

