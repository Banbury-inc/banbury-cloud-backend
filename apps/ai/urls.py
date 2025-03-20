from django.urls import path
from . import views

urlpatterns = [
    path("get_models/", views.get_models, name="get_models"),
    path("post_models/", views.post_models, name="post_models"),
]

