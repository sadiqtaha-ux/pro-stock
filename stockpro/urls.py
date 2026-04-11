"""
StockPro - URLs principales
MediCare Industries - Meknès, Maroc
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Administration Django
    path('admin/', admin.site.urls),

    # Applications locales
    path('', include('core.urls', namespace='core')),
    path('produits/', include('produits.urls', namespace='produits')),
    path('mouvements/', include('mouvements.urls', namespace='mouvements')),
    path('approvisionnement/', include('approvisionnement.urls', namespace='approvisionnement')),
    path('dashboard/', include('dashboard.urls', namespace='dashboard')),
    path('magasin/', include('magasin.urls', namespace='magasin')),

    # API REST
    path('api/v1/', include('core.api_urls')),
]

# Fichiers statiques & médias en développement
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

    # Django Debug Toolbar
    import debug_toolbar
    urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns

# Configuration de l'administration
admin.site.site_header = 'StockPro — MediCare Industries'
admin.site.site_title = 'Administration StockPro'
admin.site.index_title = 'Tableau de bord d\'administration'
