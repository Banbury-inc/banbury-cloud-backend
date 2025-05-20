from django.urls import path
from . import views

urlpatterns = [
    path("add_notification/", views.add_notification, name="add_notification"),
    path("get_notifications/", views.get_notifications, name="get_notifications"),
    path("delete_notification/", views.delete_notification, name="delete_notification"),
    path("mark_notification_as_read/", views.mark_notification_as_read, name="mark_notification_as_read"),
]
