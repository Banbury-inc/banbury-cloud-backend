from django.urls import path
from . import views

urlpatterns = [
    path("dashboard/<str:username>/", views.dashboard, name="dashboard"),
    path("get_session/<str:username>/", views.get_session, name="get_session"),
    path("get_recent_session/<str:username>/", views.get_recent_session, name="get_session"),
]
