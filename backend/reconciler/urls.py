"""URL patterns for the reconciler API."""
from django.urls import path
from . import views

app_name = 'reconciler'

urlpatterns = [
    path('discrepancies/', views.DiscrepancyListView.as_view(), name='discrepancy-list'),
    path('organizations/', views.OrganizationListView.as_view(), name='organization-list'),
    path('stats/', views.StatsView.as_view(), name='stats'),
]
