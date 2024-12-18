from django.urls import path
from . import views

urlpatterns = [
    path("update_settings/<str:username>/", views.update_settings, name="update_settings"),
]
