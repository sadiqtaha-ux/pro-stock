"""
App Core - URLs API REST
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

# Router API (à compléter avec les ViewSets)
router = DefaultRouter()

urlpatterns = [
    path('', include(router.urls)),
]
