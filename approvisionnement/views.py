"""
App Approvisionnement - Vues
4 méthodes : REAPPRO_FIXE, POINT_COMMANDE, RECOMPLETEMENT, MRP
Gestion des commandes d'achat et suggestions
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView
from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Sum, F, Count
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from .models import (
    CommandeAchat, LigneCommandeAchat,
    SuggestionAppro, ParametreAppro,
    PlanMRP, LigneMRP, MethodeApprovisionnement
)
from .forms import (
    CommandeAchatForm, LigneCommandeAchatForm,
    SuggestionApproForm, ParametreApproForm,
    PlanMRPForm
)
from .services import (
    CalculReapproFixe,
    CalculPointCommande,
    CalculRecompletement,
    CalculMRP,
)
from produits.models import Produit


# ============================================================
# TABLEAU DE BORD APPROVISIONNEMENT
# ============================================================

class ApproDashboardView(LoginRequiredMixin, TemplateView):
    """Tableau de bord de l'approvisionnement."""
    template_name = 'approvisionnement/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['nb_commandes_en_attente'] = CommandeAchat.objects.filter(
            statut=CommandeAchat.Statut.EN_ATTENTE_VALIDATION
        ).count()
        context['nb_suggestions_nouvelles'] = SuggestionAppro.objects.filter(
            statut=SuggestionAppro.Statut.NOUVELLE
        ).count()
        context['nb_produits_a_commander'] = Produit.objects.filter(
            stock_actuel__lte=F('point_commande'),
            statut='ACTIF',
        ).count()
        context['commandes_recentes'] = CommandeAchat.objects.select_related(
            'fournisseur'
        ).order_by('-date_commande')[:5]
        context['suggestions_urgentes'] = SuggestionAppro.objects.filter(
            statut=SuggestionAppro.Statut.NOUVELLE,
            urgente=True,
        ).select_related('produit', 'fournisseur')[:10]
        return context


# ============================================================
# COMMANDES D'ACHAT
# ============================================================

class CommandeListeView(LoginRequiredMixin, ListView):
    """Liste des commandes d'achat."""
    model = CommandeAchat
    template_name = 'approvisionnement/commande/liste.html'
    context_object_name = 'commandes'
    paginate_by = 25

    def get_queryset(self):
        qs = CommandeAchat.objects.select_related('fournisseur', 'cree_par')
        statut = self.request.GET.get('statut')
        if statut:
            qs = qs.filter(statut=statut)
        fournisseur = self.request.GET.get('fournisseur')
        if fournisseur:
            qs = qs.filter(fournisseur_id=fournisseur)
        return qs.order_by('-date_commande')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['statuts'] = CommandeAchat.Statut.choices
        context['montant_total_en_cours'] = CommandeAchat.objects.filter(
            statut__in=[
                CommandeAchat.Statut.VALIDE,
                CommandeAchat.Statut.ENVOYE,
                CommandeAchat.Statut.PARTIELLEMENT_RECU,
            ]
        ).aggregate(total=Sum('montant_ttc'))['total'] or 0
        return context


class CommandeDetailView(LoginRequiredMixin, DetailView):
    """Détail d'une commande d'achat."""
    model = CommandeAchat
    template_name = 'approvisionnement/commande/detail.html'
    context_object_name = 'commande'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['lignes'] = self.object.lignes.select_related('produit', 'unite')
        return context


class CommandeCreerView(LoginRequiredMixin, CreateView):
    """Créer une nouvelle commande d'achat."""
    model = CommandeAchat
    form_class = CommandeAchatForm
    template_name = 'approvisionnement/commande/form.html'

    def form_valid(self, form):
        form.instance.cree_par = self.request.user
        messages.success(self.request, _("Commande créée avec succès."))
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('approvisionnement:commande-detail', kwargs={'pk': self.object.pk})


class CommandeModifierView(LoginRequiredMixin, UpdateView):
    model = CommandeAchat
    form_class = CommandeAchatForm
    template_name = 'approvisionnement/commande/form.html'

    def get_success_url(self):
        messages.success(self.request, _("Commande mise à jour."))
        return reverse_lazy('approvisionnement:commande-detail', kwargs={'pk': self.object.pk})


@login_required
def valider_commande(request, pk):
    """Valider une commande d'achat."""
    commande = get_object_or_404(CommandeAchat, pk=pk)
    if request.method == 'POST' and request.user.peut_valider:
        if commande.statut == CommandeAchat.Statut.EN_ATTENTE_VALIDATION:
            commande.statut = CommandeAchat.Statut.VALIDE
            commande.valide_par = request.user
            commande.date_validation = timezone.now()
            commande.save()
            messages.success(request, _("Commande validée avec succès."))
        else:
            messages.warning(request, _("Cette commande ne peut pas être validée."))
    return redirect('approvisionnement:commande-detail', pk=pk)


@login_required
def transformer_suggestion_en_commande(request, pk):
    """Transformer une suggestion en commande d'achat."""
    suggestion = get_object_or_404(SuggestionAppro, pk=pk)
    if request.method == 'POST' and suggestion.statut == SuggestionAppro.Statut.NOUVELLE:
        commande = CommandeAchat.objects.create(
            fournisseur=suggestion.fournisseur or suggestion.produit.fournisseur_principal,
            type_commande=CommandeAchat.TypeCommande.AUTOMATIQUE,
            methode_declenchement=suggestion.methode,
            date_commande=timezone.now().date(),
            cree_par=request.user,
        )
        LigneCommandeAchat.objects.create(
            commande=commande,
            produit=suggestion.produit,
            quantite_commandee=suggestion.quantite_suggeree,
            unite=suggestion.produit.unite_stock,
            prix_unitaire_ht=suggestion.produit.prix_unitaire_achat,
            tva=suggestion.produit.tva,
        )
        commande.recalculer_montants()
        suggestion.statut = SuggestionAppro.Statut.TRANSFORMEE
        suggestion.commande_generee = commande
        suggestion.save()
        messages.success(request, _(f"Suggestion transformée en commande {commande.numero}."))
        return redirect('approvisionnement:commande-detail', pk=commande.pk)
    return redirect('approvisionnement:suggestions-liste')


# ============================================================
# MÉTHODE 1 : RÉAPPROVISIONNEMENT À QUANTITÉ FIXE
# ============================================================

class ReapproFixeView(LoginRequiredMixin, TemplateView):
    """
    Vue de la méthode REAPPRO_FIXE.
    Affichage des produits gérés en quantité/période fixe
    et simulation du calcul.
    """
    template_name = 'approvisionnement/methodes/reappro_fixe.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['produits'] = Produit.objects.filter(
            methode_appro='REAPPRO_FIXE',
            statut='ACTIF',
        ).select_related('parametre_appro', 'unite_stock')
        return context

    def post(self, request):
        """Lancer le calcul et générer les suggestions."""
        suggestions = CalculReapproFixe.generer_suggestions()
        messages.success(request, _(f"{len(suggestions)} suggestion(s) générée(s) par la méthode Réappro Fixe."))
        return redirect('approvisionnement:suggestions-liste')


# ============================================================
# MÉTHODE 2 : POINT DE COMMANDE (ROP)
# ============================================================

class PointCommandeView(LoginRequiredMixin, TemplateView):
    """
    Vue de la méthode POINT_COMMANDE (Reorder Point).
    Affichage des produits dont le stock a atteint le point de commande.
    """
    template_name = 'approvisionnement/methodes/point_commande.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['produits_en_alerte'] = Produit.objects.filter(
            methode_appro='POINT_COMMANDE',
            statut='ACTIF',
            stock_actuel__lte=F('point_commande'),
        ).select_related('parametre_appro', 'unite_stock', 'fournisseur_principal')
        context['tous_produits_rop'] = Produit.objects.filter(
            methode_appro='POINT_COMMANDE',
            statut='ACTIF',
        ).select_related('parametre_appro', 'unite_stock')
        return context

    def post(self, request):
        """Lancer le calcul automatique du ROP."""
        suggestions = CalculPointCommande.generer_suggestions()
        messages.success(request, _(f"{len(suggestions)} suggestion(s) ROP générée(s)."))
        return redirect('approvisionnement:suggestions-liste')


# ============================================================
# MÉTHODE 3 : RÉCOMPLETEMENT (S,T)
# ============================================================

class RecompletementView(LoginRequiredMixin, TemplateView):
    """
    Vue de la méthode RECOMPLETEMENT périodique.
    Révision périodique du stock, objectif = atteindre stock cible S.
    """
    template_name = 'approvisionnement/methodes/recompletement.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['produits'] = Produit.objects.filter(
            methode_appro='RECOMPLETEMENT',
            statut='ACTIF',
        ).select_related('parametre_appro', 'unite_stock')
        return context

    def post(self, request):
        suggestions = CalculRecompletement.generer_suggestions()
        messages.success(request, _(f"{len(suggestions)} suggestion(s) de récompletement générée(s)."))
        return redirect('approvisionnement:suggestions-liste')


# ============================================================
# MÉTHODE 4 : MRP
# ============================================================

class MRPListeView(LoginRequiredMixin, ListView):
    """Liste des plans MRP."""
    model = PlanMRP
    template_name = 'approvisionnement/mrp/liste.html'
    context_object_name = 'plans_mrp'


class MRPDetailView(LoginRequiredMixin, DetailView):
    """Détail d'un plan MRP avec tableau de planification."""
    model = PlanMRP
    template_name = 'approvisionnement/mrp/detail.html'
    context_object_name = 'plan'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['lignes'] = self.object.lignes.select_related(
            'produit', 'produit__unite_stock'
        ).order_by('produit__designation', 'annee', 'semaine')
        context['produits_mrp'] = Produit.objects.filter(
            methode_appro='MRP', statut='ACTIF'
        ).distinct()
        return context


class MRPCreerView(LoginRequiredMixin, CreateView):
    """Créer un nouveau plan MRP."""
    model = PlanMRP
    form_class = PlanMRPForm
    template_name = 'approvisionnement/mrp/form.html'
    success_url = reverse_lazy('approvisionnement:mrp-liste')

    def form_valid(self, form):
        form.instance.cree_par = self.request.user
        messages.success(self.request, _("Plan MRP créé. Lancez le calcul de planification."))
        return super().form_valid(form)


@login_required
def lancer_calcul_mrp(request, pk):
    """Lancer ou relancer le calcul MRP pour un plan donné."""
    plan = get_object_or_404(PlanMRP, pk=pk)
    if request.method == 'POST':
        try:
            nb_lignes = CalculMRP.executer(plan)
            plan.statut = PlanMRP.Statut.CALCULE
            plan.save(update_fields=['statut'])
            messages.success(request, _(f"Calcul MRP exécuté : {nb_lignes} lignes générées."))
        except Exception as e:
            messages.error(request, _(f"Erreur lors du calcul MRP : {e}"))
    return redirect('approvisionnement:mrp-detail', pk=pk)


# ============================================================
# SUGGESTIONS D'APPROVISIONNEMENT
# ============================================================

class SuggestionListeView(LoginRequiredMixin, ListView):
    """Liste des suggestions d'approvisionnement."""
    model = SuggestionAppro
    template_name = 'approvisionnement/suggestions/liste.html'
    context_object_name = 'suggestions'
    paginate_by = 30

    def get_queryset(self):
        qs = SuggestionAppro.objects.select_related(
            'produit', 'fournisseur', 'produit__unite_stock'
        )
        statut = self.request.GET.get('statut', SuggestionAppro.Statut.NOUVELLE)
        if statut:
            qs = qs.filter(statut=statut)
        methode = self.request.GET.get('methode')
        if methode:
            qs = qs.filter(methode=methode)
        return qs.order_by('-urgente', '-date_suggestion')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['statuts'] = SuggestionAppro.Statut.choices
        context['methodes'] = MethodeApprovisionnement.choices
        context['nb_urgentes'] = SuggestionAppro.objects.filter(
            statut=SuggestionAppro.Statut.NOUVELLE, urgente=True
        ).count()
        return context


# ============================================================
# PARAMÈTRES D'APPROVISIONNEMENT
# ============================================================

class ParametreApproView(LoginRequiredMixin, TemplateView):
    """Paramétrage des méthodes par produit."""
    template_name = 'approvisionnement/parametres/liste.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['parametres'] = ParametreAppro.objects.select_related(
            'produit', 'produit__unite_stock'
        ).order_by('produit__designation')
        return context


@login_required
def calculer_parametres_produit(request, produit_pk):
    """Recalculer les paramètres d'approvisionnement d'un produit."""
    produit = get_object_or_404(Produit, pk=produit_pk)
    try:
        param = produit.parametre_appro
        param.calculer_qec_wilson()
        param.calculer_stock_securite()
        param.calculer_point_commande()
        param.save()
        # Mettre à jour le produit
        produit.stock_securite = param.stock_securite_calcule or 0
        produit.point_commande = param.point_commande_calcule or 0
        produit.quantite_economique = param.qec_calcule or 0
        produit.save(update_fields=['stock_securite', 'point_commande', 'quantite_economique'])
        messages.success(request, _(f"Paramètres recalculés pour {produit.designation}."))
    except ParametreAppro.DoesNotExist:
        messages.error(request, _("Aucun paramètre d'approvisionnement configuré pour ce produit."))
    return redirect('produits:produit-detail', pk=produit_pk)
