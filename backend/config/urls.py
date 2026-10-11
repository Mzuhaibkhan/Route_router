"""URL configuration for Spotter AI project."""
from django.urls import path, include

urlpatterns = [
    path('api/', include('api.urls')),
]
