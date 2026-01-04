"""
URL configuration for skinmp project.
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('social_django.urls', namespace='social')),
    path('', include('core.urls')),
    path('login/', RedirectView.as_view(url='/login/steam/', permanent=False), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]
