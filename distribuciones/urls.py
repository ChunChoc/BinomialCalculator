from django.urls import path
from . import views

app_name = 'distribuciones'

urlpatterns = [
    path('binomial/', views.binomial_view, name='binomial'),
    path('aceptacion-lotes/', views.acceptance_sampling_view, name='acceptance_sampling'),
    path('colas/mm1/', views.mm1_queue_view, name='mm1_queue'),
    path('poisson/', views.poisson_view, name='poisson'),
    path('api/distributions/', views.available_distributions, name='api_distributions'),
]
