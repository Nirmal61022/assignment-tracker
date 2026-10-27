"""
URL configuration for Assignment Tracker project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('tracker.urls')),
]

handler404 = 'tracker.views.custom_404_view'
handler500 = 'tracker.views.custom_500_view'

