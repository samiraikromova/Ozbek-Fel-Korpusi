from django.urls import path
from . import views


urlpatterns = [
    path('', views.index, name='index'),
    path('qidiruv/', views.search_results, name='search_results'),
    path('statistika/', views.statistics_view, name='statistics'),  # Changed from 'statistics'
]