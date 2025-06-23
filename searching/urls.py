from django.urls import path
from . import views

urlpatterns = [
    path('', views.search_active_document, name='index'),
    path('res/', views.results_page, name='result_page')
]
