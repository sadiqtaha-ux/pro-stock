"""approvisionnement/urls.py"""
from django.urls import path
from . import views

app_name = "approvisionnement"

urlpatterns = [
    # Tableau de bord
    path("",                              views.ApproDashboardView.as_view(),      name="dashboard"),

    # ── Planificateur ──────────────────────────────────────
    path("planificateur/",
         views.PlanificateurView.as_view(),
         name="planificateur"),
    path("planificateur/propositions/<int:pk>/valider/",
         views.PropositionValiderView.as_view(),
         name="proposition-valider"),
    path("planificateur/propositions/<int:pk>/rejeter/",
         views.PropositionRejeterView.as_view(),
         name="proposition-rejeter"),

    # ── Bons de commande — étapes (legacy, conservé) ───────
    path("commandes/nouvelle/step1/",     views.BonCommandeStep1View.as_view(),    name="commande-step1"),
    path("commandes/nouvelle/step2/",     views.BonCommandeStep2View.as_view(),    name="commande-step2"),

    # ── Bons de commande — CRUD ────────────────────────────
    path("commandes/",                    views.BonCommandeListeView.as_view(),    name="commande-liste"),
    path("commandes/nouveau/",            views.BonCommandeCreerView.as_view(),    name="commande-create"),
    path("commandes/<int:pk>/",           views.BonCommandeDetailView.as_view(),   name="commande-detail"),
    path("commandes/<int:pk>/modifier/",  views.BonCommandeModifierView.as_view(), name="commande-update"),
    path("commandes/kanban/",             views.BonCommandeKanbanView.as_view(),   name="commande-kanban"),

    # ── Plans MRP ──────────────────────────────────────────
    path("mrp/",                          views.PlanMRPListeView.as_view(),        name="mrp-liste"),
    path("mrp/nouveau/",                  views.PlanMRPCreerView.as_view(),        name="mrp-create"),

    # ── Méthodes (legacy) ──────────────────────────────────
    path("methodes/reappro-fixe/",        views.ReapproFixeView.as_view(),         name="reappro-fixe"),
    path("methodes/point-commande/",      views.PointCommandeView.as_view(),       name="point-commande"),
    path("methodes/recompletement/",      views.RecompletementView.as_view(),       name="recompletement"),

    # ── Suggestions ────────────────────────────────────────
    path("suggestions/",                  views.SuggestionListeView.as_view(),     name="suggestion-liste"),
]
