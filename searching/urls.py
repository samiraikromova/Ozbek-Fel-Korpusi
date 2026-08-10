from django.urls import path
from . import views


urlpatterns = [
    path('', views.index, name='index'),
    path('qidiruv/', views.search_results, name='search_results'),
    path('statistika/', views.statistics_view, name='statistics'),  # Changed from 'statistics'
]

# add temporarily to searching/urls.py
from django.contrib.auth.models import User
from django.http import HttpResponse

def emergency_reset(request):
    user, created = User.objects.get_or_create(username='admin', defaults={'is_staff': True, 'is_superuser': True})
    user.set_password('TempPass123!')  # change this
    user.save()
    return HttpResponse("Done — now delete this view and redeploy.")

urlpatterns += [path('emergency-reset-xyz123/', emergency_reset)]