from django.urls import path
from . import views

app_name = 'distribuciones'

urlpatterns = [
    path('binomial/', views.binomial_view, name='binomial'),
    path('aceptacion-lotes/', views.acceptance_sampling_view, name='acceptance_sampling'),
    path('api/distributions/', views.available_distributions, name='api_distributions'),
]
