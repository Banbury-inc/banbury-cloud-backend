from django.urls import path
from . import views

urlpatterns = [
    path("add_task/<str:username>/", views.add_task, name="add_task"),
    path("update_task/<str:username>/", views.update_task, name="update_task"),
    path("fail_task/<str:username>/", views.fail_task, name="update_task"),
]
