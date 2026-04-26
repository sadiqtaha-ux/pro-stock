"""approvisionnement/urls.py"""
from django.urls import path
from . import views

app_name = "approvisionnement"

urlpatterns = [
    # Tableau de bord
    path("",                              views.ApproDashboardView.as_view(),      name="dashboard"),

    # ── Planificateur & Commandes à valider ────────────────
    path("commandes-a-valider/",
         views.PlanificateurView.as_view(),
         name="commandes-a-valider"),
    path("planificateur/propositions/<int:pk>/valider/",
         views.PropositionValiderView.as_view(),
         name="proposition-valider"),
    path("planificateur/propositions/<int:pk>/rejeter/",
         views.PropositionRejeterView.as_view(),
         name="proposition-rejeter"),

    # ── Bons de commande — CRUD ────────────────────────────
    path("commandes/",                    views.BonCommandeListeView.as_view(),    name="commande-liste"),
    path("commandes/<int:pk>/",           views.BonCommandeDetailView.as_view(),   name="commande-detail"),
    path("commandes/<int:pk>/modifier/",  views.BonCommandeModifierView.as_view(), name="commande-update"),
    path("commandes/kanban/",             views.BonCommandeKanbanView.as_view(),   name="commande-kanban"),

    # ── Plans MRP ──────────────────────────────────────────
    path("mrp/",                          views.PlanMRPListeView.as_view(),        name="mrp-liste"),
    path("mrp/nouveau/",                  views.PlanMRPCreerView.as_view(),        name="mrp-create"),
    path("mrp/simulateur/",               views.SimulateurMRPView.as_view(),       name="simulateur-mrp"),

    # ── Suggestions ────────────────────────────────────────
    path("suggestions/",                  views.SuggestionListeView.as_view(),     name="suggestion-liste"),
]
