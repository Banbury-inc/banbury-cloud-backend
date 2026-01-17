from django.urls import path
from . import views

urlpatterns = [
    path("get_analytics/", views.get_analytics, name="get_analytics"),
    path("add_file_request/", views.add_file_request, name="add_file_request"),
    path("add_file_request_success/", views.add_file_request_success, name="add_file_request_success"),
    path("get_file_type_analytics/", views.get_file_type_analytics, name="get_file_type_analytics"),
    path("track_file_upload/", views.track_file_upload, name="track_file_upload"),
    # New analytics endpoints
    path("get_api_usage_analytics/", views.get_api_usage_analytics, name="get_api_usage_analytics"),
    path("track_user_engagement/", views.track_user_engagement, name="track_user_engagement"),
    path("get_user_engagement_analytics/", views.get_user_engagement_analytics, name="get_user_engagement_analytics"),
    path("get_retention_analytics/", views.get_retention_analytics, name="get_retention_analytics"),
    path("track_feature_usage/", views.track_feature_usage, name="track_feature_usage"),
    path("get_feature_usage_analytics/", views.get_feature_usage_analytics, name="get_feature_usage_analytics"),
    path("track_error/", views.track_error, name="track_error"),
    path("get_error_analytics/", views.get_error_analytics, name="get_error_analytics"),
    path("track_page_time/", views.track_page_time, name="track_page_time"),
    path("get_page_time_analytics/", views.get_page_time_analytics, name="get_page_time_analytics"),
    path("track_user_journey_event/", views.track_user_journey_event, name="track_user_journey_event"),
    path("get_user_journey_analytics/", views.get_user_journey_analytics, name="get_user_journey_analytics"),
]

