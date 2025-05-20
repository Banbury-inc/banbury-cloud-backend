from django.urls import path
from . import views

urlpatterns = [
    path("update_settings/", views.update_settings, name="update_settings"),
    path("get_settings/", views.get_settings, name="get_settings"),
    path("delete_account/", views.delete_account, name="delete_account"),
]
