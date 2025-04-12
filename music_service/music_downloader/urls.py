# music_downloader/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('download/', views.download_song, name='download_song'),
    path('status/', views.get_status, name='get_status'),
    path('search/', views.search_music, name='search_music'),
]
