"""
App Core - Vues
Authentification, profil, tableau de bord d'accueil
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.views import View
from django.views.generic import (
    TemplateView, ListView, DetailView,
    CreateView, UpdateView, DeleteView
)
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.db.models import Q

from .models import Utilisateur, JournalActivite, Notification, ParametreApplication
from core.mixins import KanbanListMixin, ExportMixin
from .forms import (
    ConnexionForm,
    ProfilForm,
    ChangerMotDePasseForm,
    UtilisateurCreationForm,
    UtilisateurModificationForm,
)


# ============================================================
# AUTHENTIFICATION
# ============================================================

class ConnexionView(View):
    """Vue de connexion utilisateur."""
    template_name = 'core/auth/connexion.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('dashboard:index')
        form = ConnexionForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = ConnexionForm(data=request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                if user.est_actif:
                    login(request, user)
                    user.date_derniere_connexion = timezone.now()
                    user.save(update_fields=['date_derniere_connexion'])
                    # Journal d'activité
                    JournalActivite.objects.create(
                        utilisateur=user,
                        action=JournalActivite.TypeAction.CONNEXION,
                        modele='Utilisateur',
                        objet_id=str(user.pk),
                        description=f"Connexion de {user.username}",
                        adresse_ip=request.META.get('REMOTE_ADDR'),
                    )
                    next_url = request.GET.get('next', 'dashboard:index')
                    messages.success(request, _(f"Bienvenue, {user.get_full_name() or user.username} !"))
                    return redirect(next_url)
                else:
                    messages.error(request, _("Votre compte est désactivé. Contactez l'administrateur."))
            else:
                messages.error(request, _("Identifiant ou mot de passe incorrect."))
        return render(request, self.template_name, {'form': form})


class DeconnexionView(LoginRequiredMixin, View):
    """Vue de déconnexion."""

    def post(self, request):
        JournalActivite.objects.create(
            utilisateur=request.user,
            action=JournalActivite.TypeAction.DECONNEXION,
            modele='Utilisateur',
            objet_id=str(request.user.pk),
            description=f"Déconnexion de {request.user.username}",
            adresse_ip=request.META.get('REMOTE_ADDR'),
        )
        logout(request)
        messages.info(request, _("Vous avez été déconnecté avec succès."))
        return redirect('core:login')


# ============================================================
# PROFIL UTILISATEUR
# ============================================================

class ProfilView(LoginRequiredMixin, TemplateView):
    """Vue profil de l'utilisateur connecté."""
    template_name = 'core/profil/profil.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_profil'] = ProfilForm(instance=self.request.user)
        context['form_mdp'] = ChangerMotDePasseForm(user=self.request.user)
        context['activites_recentes'] = JournalActivite.objects.filter(
            utilisateur=self.request.user
        ).order_by('-date_action')[:10]
        return context

    def post(self, request):
        action = request.POST.get('action')

        if action == 'profil':
            form = ProfilForm(request.POST, request.FILES, instance=request.user)
            if form.is_valid():
                form.save()
                messages.success(request, _("Profil mis à jour avec succès."))
                return redirect('core:profil')
            else:
                messages.error(request, _("Erreur lors de la mise à jour du profil."))

        elif action == 'mot_de_passe':
            form = ChangerMotDePasseForm(user=request.user, data=request.POST)
            if form.is_valid():
                user = form.save()
                update_session_auth_hash(request, user)
                messages.success(request, _("Mot de passe changé avec succès."))
                return redirect('core:profil')
            else:
                messages.error(request, _("Erreur lors du changement de mot de passe."))

        return redirect('core:profil')


# ============================================================
# GESTION DES UTILISATEURS (ADMIN)
# ============================================================

class UtilisateurListeView(LoginRequiredMixin, UserPassesTestMixin, ExportMixin, ListView):
    """Liste des utilisateurs — Admin uniquement."""
    model = Utilisateur
    template_name = 'core/utilisateurs/liste.html'
    context_object_name = 'utilisateurs'
    paginate_by = 25
    export_fields = ['username', 'first_name', 'last_name', 'email', 'role', 'est_actif']
    export_headers = ['Identifiant', 'Prénom', 'Nom', 'Email', 'Rôle', 'Actif']

    def test_func(self):
        return self.request.user.est_admin

    def get_queryset(self):
        # On affiche tout sauf les superutilisateurs (sauf si l'utilisateur courant est lui-même superutilisateur ?)
        # Règle demandée : "exclure les superusers de la liste visible"
        qs = Utilisateur.objects.filter(is_superuser=False).order_by('last_name', 'first_name')
        
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(
                Q(username__icontains=q) |
                Q(first_name__icontains=q) |
                Q(last_name__icontains=q) |
                Q(email__icontains=q)
            )
        role = self.request.GET.get('role')
        if role:
            qs = qs.filter(role=role)
        return qs

    def get(self, request, *args, **kwargs):
        export_type = request.GET.get('export')
        if export_type == 'csv':
            return self.render_to_csv(self.get_queryset(), filename_prefix="utilisateurs")
        elif export_type == 'pdf':
            return self.render_to_pdf(self.get_queryset(), title="Registre des Utilisateurs", filename_prefix="utilisateurs")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['roles'] = Utilisateur.Role.choices
        context['total'] = Utilisateur.objects.count()
        context['actifs'] = Utilisateur.objects.filter(est_actif=True).count()
        return context


class UtilisateurCreerView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """Créer un nouvel utilisateur."""
    model = Utilisateur
    form_class = UtilisateurCreationForm
    template_name = 'core/utilisateurs/form.html'
    success_url = reverse_lazy('core:utilisateurs-liste')

    def test_func(self):
        return self.request.user.est_admin

    def form_valid(self, form):
        from .utils import log_action
        response = super().form_valid(form)
        log_action(
            self.request,
            JournalActivite.TypeAction.CREATION,
            'Utilisateur',
            self.object.pk,
            f"Création de l'utilisateur {self.object.username}"
        )
        messages.success(self.request, _("Utilisateur créé avec succès."))
        return response


class UtilisateurModifierView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Modifier un utilisateur existant."""
    model = Utilisateur
    form_class = UtilisateurModificationForm
    template_name = 'core/utilisateurs/form.html'
    success_url = reverse_lazy('core:utilisateurs-liste')

    def test_func(self):
        return self.request.user.est_admin

    def form_valid(self, form):
        from .utils import log_action
        response = super().form_valid(form)
        log_action(
            self.request,
            JournalActivite.TypeAction.MODIFICATION,
            'Utilisateur',
            self.object.pk,
            f"Modification de l'utilisateur {self.object.username}"
        )
        messages.success(self.request, _("Utilisateur modifié avec succès."))
        return response

class UtilisateurDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """Détail d'un utilisateur."""
    model = Utilisateur
    template_name = 'core/utilisateurs/detail.html'
    context_object_name = 'u'

    def test_func(self):
        return self.request.user.est_admin

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['activites'] = JournalActivite.objects.filter(utilisateur=self.object).order_by('-date_action')[:20]
        return context

class UtilisateurToggleActifView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Activer/Désactiver un utilisateur."""
    def test_func(self):
        return self.request.user.est_admin

    def post(self, request, pk):
        from .utils import log_action
        user = get_object_or_404(Utilisateur, pk=pk)
        if user == request.user:
            messages.error(request, _("Vous ne pouvez pas vous désactiver vous-même."))
            return redirect('core:utilisateurs-liste')
        
        user.est_actif = not user.est_actif
        user.is_active = user.est_actif # Synchroniser avec Django
        user.save()
        
        action = JournalActivite.TypeAction.ACTIVATION if user.est_actif else JournalActivite.TypeAction.DESACTIVATION
        log_action(
            request,
            action,
            'Utilisateur',
            user.pk,
            f"{'Activation' if user.est_actif else 'Désactivation'} de l'utilisateur {user.username}"
        )
        
        messages.success(request, _(f"Utilisateur {user.username} {'activé' if user.est_actif else 'désactivé'}."))
        return redirect('core:utilisateurs-liste')


# ============================================================
# NOTIFICATIONS
# ============================================================

class NotificationsView(LoginRequiredMixin, KanbanListMixin, ExportMixin, ListView):
    """Vue des notifications de l'utilisateur connecté."""
    model = Notification
    template_name = 'core/notifications/liste.html'
    kanban_template_name = 'core/notifications/kanban.html'
    context_object_name = 'notifications_list'
    paginate_by = 20
    export_fields = ['date_envoi', 'type_notification', 'priorite', 'titre', 'message', 'lue']
    export_headers = ['Date', 'Type', 'Priorité', 'Titre', 'Message', 'Lue']

    def get_queryset(self):
        qs = Notification.objects.filter(destinataire=self.request.user)
        
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(Q(titre__icontains=q) | Q(message__icontains=q))
            
        type_notif = self.request.GET.get('type')
        if type_notif:
            qs = qs.filter(type_notification=type_notif)
            
        priorite = self.request.GET.get('priorite')
        if priorite:
            qs = qs.filter(priorite=priorite)
            
        lue = self.request.GET.get('lue')
        if lue == '1':
            qs = qs.filter(lue=True)
        elif lue == '0':
            qs = qs.filter(lue=False)
            
        return qs.order_by('-date_envoi')

    def get(self, request, *args, **kwargs):
        export_type = request.GET.get('export')
        if export_type == 'csv':
            return self.render_to_csv(self.get_queryset(), filename_prefix="notifications")
        elif export_type == 'pdf':
            return self.render_to_pdf(self.get_queryset(), title="Mes Alertes & Notifications", filename_prefix="notifications")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['types_notif'] = Notification.TypeNotification.choices
        context['priorites'] = Notification.Priorite.choices
        
        # Ajout des alertes "Live"
        from produits.models import MatierePremiere, ProduitFini
        from approvisionnement.models import BonCommande, PropositionCommande
        from magasin.models import Emplacement
        from django.db.models import F
        from django.utils import timezone
        
        today = timezone.now().date()
        live_alerts = []
        
        # Ruptures MP
        for mp in MatierePremiere.objects.filter(stock_actuel__lte=0, actif=True):
            live_alerts.append({'type': 'STOCK', 'priorite': 'HAUTE', 'titre': _("Matière en rupture"), 'message': f"La matière {mp.nom} est en rupture.", 'date': mp.date_modification})
        
        # Ruptures PF
        for pf in ProduitFini.objects.filter(stock_actuel__lte=0, actif=True):
            live_alerts.append({'type': 'STOCK', 'priorite': 'HAUTE', 'titre': _("Produit fini en rupture"), 'message': f"Le produit {pf.nom} est épuisé.", 'date': pf.date_modification})
            
        # Retards BC
        for bc in BonCommande.objects.filter(statut__in=['ENVOYE', 'CONFIRME'], date_reception_prevue__lt=today):
            live_alerts.append({'type': 'COMMANDE', 'priorite': 'HAUTE', 'titre': _("Retard de livraison"), 'message': f"BC {bc.reference} ({bc.fournisseur.nom}) en retard.", 'date': bc.date_creation})
            
        # Props
        props_count = PropositionCommande.objects.filter(statut=PropositionCommande.Statut.EN_ATTENTE).count()
        if props_count > 0:
            live_alerts.append({'type': 'COMMANDE', 'priorite': 'NORMALE', 'titre': _("Propositions MRP"), 'message': f"{props_count} propositions à valider.", 'date': timezone.now()})
            
        # Emplacements
        for em in Emplacement.objects.filter(statut='BLOQUE'):
            live_alerts.append({'type': 'SYSTEME', 'priorite': 'NORMALE', 'titre': _("Emplacement bloqué"), 'message': f"L'emplacement {em.code} est bloqué.", 'date': timezone.now()})
            
        context['live_alerts'] = live_alerts
        return context


@login_required
def marquer_notification_lue(request, pk):
    """Marquer une notification comme lue (AJAX)."""
    notification = get_object_or_404(Notification, pk=pk, destinataire=request.user)
    notification.marquer_lue()
    return JsonResponse({'status': 'ok', 'non_lues': request.user.notifications.filter(lue=False).count()})


@login_required
def marquer_toutes_lues(request):
    """Marquer toutes les notifications comme lues."""
    request.user.notifications.filter(lue=False).update(
        lue=True,
        date_lecture=timezone.now()
    )
    messages.success(request, _("Toutes les notifications ont été marquées comme lues."))
    return redirect('core:notifications')


# ============================================================
# JOURNAL D'ACTIVITÉ
# ============================================================

class JournalView(LoginRequiredMixin, UserPassesTestMixin, KanbanListMixin, ExportMixin, ListView):
    """Journal d'activité global — Admin uniquement."""
    model = JournalActivite
    template_name = 'core/journal/liste.html'
    kanban_template_name = 'core/journal/kanban.html'
    context_object_name = 'activites'
    paginate_by = 50
    export_fields = ['date_action', 'utilisateur__username', 'action', 'modele', 'description', 'adresse_ip']
    export_headers = ['Date', 'Utilisateur', 'Action', 'Modèle', 'Description', 'Adresse IP']

    def test_func(self):
        return self.request.user.est_admin

    def get_queryset(self):
        qs = JournalActivite.objects.select_related('utilisateur').order_by('-date_action')
        
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(Q(description__icontains=q) | Q(modele__icontains=q))
            
        utilisateur_id = self.request.GET.get('utilisateur')
        if utilisateur_id:
            qs = qs.filter(utilisateur_id=utilisateur_id)
            
        action = self.request.GET.get('action')
        if action:
            qs = qs.filter(action=action)
            
        modele = self.request.GET.get('modele')
        if modele:
            qs = qs.filter(modele__icontains=modele)
            
        niveau = self.request.GET.get('niveau')
        if niveau:
            qs = qs.filter(niveau=niveau)
            
        date_from = self.request.GET.get('date_from')
        if date_from:
            qs = qs.filter(date_action__date__gte=date_from)
            
        date_to = self.request.GET.get('date_to')
        if date_to:
            qs = qs.filter(date_action__date__lte=date_to)
            
        return qs

    def get(self, request, *args, **kwargs):
        export_type = request.GET.get('export')
        if export_type == 'csv':
            return self.render_to_csv(self.get_queryset(), filename_prefix="journal_activite")
        elif export_type == 'pdf':
            return self.render_to_pdf(self.get_queryset(), title="Journal d'Activité Système", filename_prefix="journal_activite")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['utilisateurs'] = Utilisateur.objects.filter(is_active=True)
        context['statuts_choices'] = JournalActivite.TypeAction.choices
        context['modeles'] = JournalActivite.objects.values_list('modele', flat=True).distinct()
        return context


# ============================================================
# PARAMÈTRES APPLICATION
# ============================================================

class ParametresView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """Gestion des paramètres applicatifs."""
    model = ParametreApplication
    template_name = 'core/parametres/liste.html'
    context_object_name = 'parametres'

    def test_func(self):
        return self.request.user.est_admin
