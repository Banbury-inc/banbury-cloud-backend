from django.urls import path
from . import views

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("get_session/", views.get_session, name="get_session"),
    path("get_recent_session/", views.get_recent_session, name="get_session"),
]
