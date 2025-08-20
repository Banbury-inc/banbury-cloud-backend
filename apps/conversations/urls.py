from django.urls import path
from . import views

urlpatterns = [
    path("save/", views.save_conversation, name="save_conversation"),
    path("list/", views.get_conversations, name="get_conversations"),
    path("<str:conversation_id>/", views.get_conversation, name="get_conversation"),
    path("<str:conversation_id>/delete/", views.delete_conversation, name="delete_conversation"),
    path("<str:conversation_id>/title/", views.update_conversation_title, name="update_conversation_title"),
]
