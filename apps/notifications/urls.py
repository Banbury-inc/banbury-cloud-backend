from django.urls import path
from . import views

urlpatterns = [
    path("add_notification/<str:username>/", views.add_notification, name="add_notification"),
    path("get_notifications/<str:username>/", views.get_notifications, name="get_notifications"),
    path("delete_notification/<str:username>/", views.delete_notification, name="delete_notification"),
    path("mark_notification_as_read/", views.mark_notification_as_read, name="mark_notification_as_read"),
]
