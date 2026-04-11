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

class UtilisateurListeView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """Liste des utilisateurs — Admin uniquement."""
    model = Utilisateur
    template_name = 'core/utilisateurs/liste.html'
    context_object_name = 'utilisateurs'
    paginate_by = 25

    def test_func(self):
        return self.request.user.est_admin

    def get_queryset(self):
        qs = Utilisateur.objects.all().order_by('last_name', 'first_name')
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
        messages.success(self.request, _("Utilisateur créé avec succès."))
        return super().form_valid(form)


class UtilisateurModifierView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Modifier un utilisateur existant."""
    model = Utilisateur
    form_class = UtilisateurModificationForm
    template_name = 'core/utilisateurs/form.html'
    success_url = reverse_lazy('core:utilisateurs-liste')

    def test_func(self):
        return self.request.user.est_admin


# ============================================================
# NOTIFICATIONS
# ============================================================

class NotificationsView(LoginRequiredMixin, ListView):
    """Vue des notifications de l'utilisateur connecté."""
    model = Notification
    template_name = 'core/notifications/liste.html'
    context_object_name = 'notifications'
    paginate_by = 20

    def get_queryset(self):
        return Notification.objects.filter(
            destinataire=self.request.user
        ).order_by('-date_envoi')


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

class JournalView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """Journal d'activité global — Admin uniquement."""
    model = JournalActivite
    template_name = 'core/journal/liste.html'
    context_object_name = 'activites'
    paginate_by = 50

    def test_func(self):
        return self.request.user.est_admin

    def get_queryset(self):
        qs = JournalActivite.objects.select_related('utilisateur').order_by('-date_action')
        utilisateur_id = self.request.GET.get('utilisateur')
        if utilisateur_id:
            qs = qs.filter(utilisateur_id=utilisateur_id)
        action = self.request.GET.get('action')
        if action:
            qs = qs.filter(action=action)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['utilisateurs'] = Utilisateur.objects.all()
        context['actions'] = JournalActivite.TypeAction.choices
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
