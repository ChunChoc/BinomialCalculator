from django.urls import path
from . import views

app_name = 'data_manager'

urlpatterns = [
    path('', views.upload_view, name='upload'),
    path('calculate/', views.calculate_auto_view, name='calculate'),
    path('hypergeometric/', views.hypergeometric_view, name='hypergeometric'),
    path('api/column-categories/', views.get_column_categories, name='api_column_categories'),
    path('api/analyze-column/', views.analyze_column, name='api_analyze_column'),
    path('clear/', views.clear_session, name='clear_session'),
]
