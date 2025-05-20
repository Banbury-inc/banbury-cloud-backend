from django.urls import path
from . import views

urlpatterns = [
    path("add_task/", views.add_task, name="add_task"),
    path("update_task/", views.update_task, name="update_task"),
    path("fail_task/", views.fail_task, name="update_task"),
]
