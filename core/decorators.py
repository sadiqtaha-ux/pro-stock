"""
core/decorators.py
Décorateurs de contrôle d'accès selon le rôle utilisateur (MediCare StockPro).
"""
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.utils.translation import gettext_lazy as _

from .models import Utilisateur


def _redirect_forbidden(request):
    messages.error(request, _("Vous n'avez pas les droits nécessaires pour accéder à cette page."))
    return redirect("dashboard:index")


# ─────────────────────────────────────────────
# @admin_required — ADMIN uniquement
# ─────────────────────────────────────────────

def admin_required(view_func):
    """Restreint la vue aux utilisateurs ayant le rôle ADMIN."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("core:login")
        if request.user.role == Utilisateur.Role.ADMIN:
            return view_func(request, *args, **kwargs)
        return _redirect_forbidden(request)
    return wrapper


# ─────────────────────────────────────────────
# @gestionnaire_required — ADMIN + RESPONSABLE_STOCK + MAGASINIER
# ─────────────────────────────────────────────

def gestionnaire_required(view_func):
    """
    Restreint la vue aux gestionnaires de stock.
    Accepte : ADMIN, RESPONSABLE_STOCK, MAGASINIER.
    """
    ROLES_AUTORISES = {
        Utilisateur.Role.ADMIN,
        Utilisateur.Role.RESPONSABLE_STOCK,
        Utilisateur.Role.MAGASINIER,
    }

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("core:login")
        if request.user.role in ROLES_AUTORISES:
            return view_func(request, *args, **kwargs)
        return _redirect_forbidden(request)
    return wrapper


# ─────────────────────────────────────────────
# @acheteur_required — ADMIN + ACHETEUR
# ─────────────────────────────────────────────

def acheteur_required(view_func):
    """
    Restreint la vue aux acheteurs.
    Accepte : ADMIN, ACHETEUR.
    """
    ROLES_AUTORISES = {
        Utilisateur.Role.ADMIN,
        Utilisateur.Role.ACHETEUR,
    }

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("core:login")
        if request.user.role in ROLES_AUTORISES:
            return view_func(request, *args, **kwargs)
        return _redirect_forbidden(request)
    return wrapper


# ─────────────────────────────────────────────
# Mixin Django CBV
# ─────────────────────────────────────────────

class AdminRequiredMixin:
    """Mixin pour les class-based views — ADMIN uniquement."""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("core:login")
        if request.user.role != Utilisateur.Role.ADMIN:
            return _redirect_forbidden(request)
        return super().dispatch(request, *args, **kwargs)


class GestionnaireRequiredMixin:
    """Mixin pour les class-based views — ADMIN + Gestionnaires."""
    ROLES_AUTORISES = {
        Utilisateur.Role.ADMIN,
        Utilisateur.Role.RESPONSABLE_STOCK,
        Utilisateur.Role.MAGASINIER,
    }

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("core:login")
        if request.user.role not in self.ROLES_AUTORISES:
            return _redirect_forbidden(request)
        return super().dispatch(request, *args, **kwargs)


class AcheteurRequiredMixin:
    """Mixin pour les class-based views — ADMIN + ACHETEUR."""
    ROLES_AUTORISES = {
        Utilisateur.Role.ADMIN,
        Utilisateur.Role.ACHETEUR,
    }

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("core:login")
        if request.user.role not in self.ROLES_AUTORISES:
            return _redirect_forbidden(request)
        return super().dispatch(request, *args, **kwargs)
