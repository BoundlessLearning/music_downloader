"""
URL configuration for music_service project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

from music_service.settings import BASE_URL

base_url = BASE_URL.strip('/')

urlpatterns = [
    path("admin/", admin.site.urls),
    path(f'{base_url}/', TemplateView.as_view(template_name='index.html'), name='index'),
    path(f'{base_url}/', include('music_downloader.urls')),
]
