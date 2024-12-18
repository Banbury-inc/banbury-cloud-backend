from django.urls import path
from . import views

urlpatterns = [
    path("update_profile/<str:username>/", views.update_user_profile, name="update_profile"),
    path("change_profile/<str:username>/<str:password>/<str:first_name>/<str:last_name>/<str:email>/",views.change_profile, name="change_profile"),
]
