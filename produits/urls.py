"""produits/urls.py"""
from django.urls import path
from . import views

app_name = "produits"

urlpatterns = [
    # Matières premières
    path("",                               views.MatiereListeView.as_view(),             name="matiere-liste"),
    path("nouvelle/methode/",              views.MatiereChoisirMethodeView.as_view(),     name="matiere-choisir-methode"),
    path("nouvelle/",                      views.MatiereCreerView.as_view(),              name="matiere-create"),
    path("<int:pk>/",                      views.MatiereDetailView.as_view(),             name="matiere-detail"),
    path("<int:pk>/modifier/",             views.MatiereModifierView.as_view(),           name="matiere-update"),
    path("<int:pk>/parametres/",           views.MatiereParametresMethodeView.as_view(),  name="matiere-parametres"),
    path("<int:pk>/supprimer/",            views.MatiereSuppressionView.as_view(),        name="matiere-delete"),

    # Fournisseurs
    path("fournisseurs/",                  views.FournisseurListeView.as_view(),          name="fournisseur-liste"),
    path("fournisseurs/nouveau/",          views.FournisseurCreerView.as_view(),          name="fournisseur-create"),
    path("fournisseurs/<int:pk>/modifier/", views.FournisseurModifierView.as_view(),      name="fournisseur-update"),

    # Unités de mesure
    path("unites/",                        views.UniteListeView.as_view(),                name="unite-liste"),

    # API
    path("api/search/",                    views.matiere_search_api,                      name="matiere-search"),
]
