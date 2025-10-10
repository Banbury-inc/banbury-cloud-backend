from django.urls import path
from . import views

urlpatterns = [
    path("get_analytics/", views.get_analytics, name="get_analytics"),
    path("add_file_request/", views.add_file_request, name="add_file_request"),
    path("add_file_request_success/", views.add_file_request_success, name="add_file_request_success"),
    path("get_file_type_analytics/", views.get_file_type_analytics, name="get_file_type_analytics"),
    path("track_file_upload/", views.track_file_upload, name="track_file_upload"),
]

