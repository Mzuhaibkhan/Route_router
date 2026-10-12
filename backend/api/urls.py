"""
URL configuration for Route Radar API endpoints.
"""
from api import views
from django.urls import path

app_name = "api"

urlpatterns = [
    path("routes/analyze", views.analyze_routes, name="analyze_routes"),
    path("routes/demo", views.demo_fixture, name="demo_fixture"),
    path("routes/plan", views.plan_route, name="plan_route"),
    path("routes/risk", views.assess_risk, name="assess_risk"),
    path("geocode/autocomplete", views.geocode_autocomplete, name="geocode_autocomplete"),
]
