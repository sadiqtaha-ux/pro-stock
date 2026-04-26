"""produits/urls.py"""
from django.urls import path
from . import views

app_name = "produits"

urlpatterns = [
    # Matières premières
    path("",                               views.MatiereListeView.as_view(),             name="matiere-liste"),
    path("nouvelle/methode/",              views.MatiereChoisirMethodeView.as_view(),     name="matiere-choisir-methode"),
    path("nouvelle/informations/",         views.MatiereCreateInfoView.as_view(),         name="matiere-create-info"),
    path("nouvelle/parametres/",           views.MatiereCreateParamsView.as_view(),       name="matiere-create-params"),
    path("nouvelle/annuler/",              views.MatiereCreationAnnulerView.as_view(),    name="matiere-create-cancel"),
    path("nouvelle/",                      views.MatiereCreerView.as_view(),              name="matiere-create"), # Legacy/Redirect
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

    # Produits Finis
    path("produits-finis/",                 views.ProduitFiniListeView.as_view(),          name="produit-fini-liste"),
    path("produits-finis/nouveau/",         views.ProduitFiniCreerView.as_view(),          name="produit-fini-create"),
    path("produits-finis/<int:pk>/",         views.ProduitFiniDetailView.as_view(),         name="produit-fini-detail"),
    path("produits-finis/<int:pk>/modifier/", views.ProduitFiniModifierView.as_view(),      name="produit-fini-update"),
    path("produits-finis/<int:pk>/supprimer/", views.ProduitFiniSupprimerView.as_view(),     name="produit-fini-delete"),
    path("produits-finis/export/csv/",      views.export_produits_finis_csv,               name="produit-fini-export-csv"),

    # Nomenclatures (BOM)
    path("produits-finis/<int:produit_pk>/nomenclature/creer/", views.NomenclatureCreerView.as_view(), name="nomenclature-create"),
    path("nomenclatures/<int:pk>/modifier/", views.NomenclatureModifierView.as_view(), name="nomenclature-update"),
    path("nomenclatures/<int:pk>/supprimer/", views.NomenclatureSupprimerView.as_view(), name="nomenclature-delete"),
    
    # Lignes de Nomenclature
    path("nomenclatures/<int:nomenclature_pk>/lignes/ajouter/", views.LigneNomenclatureAjouterView.as_view(), name="nomenclature-ligne-add"),
    path("nomenclatures/lignes/<int:pk>/modifier/", views.LigneNomenclatureModifierView.as_view(), name="nomenclature-ligne-update"),
    path("nomenclatures/lignes/<int:pk>/supprimer/", views.LigneNomenclatureSupprimerView.as_view(), name="nomenclature-ligne-delete"),
]


