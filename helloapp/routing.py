
from django.urls import path
from helloapp.consumers import YourConsumer  # Make sure this matches the actual name

websocket_urlpatterns = [
    path('ws/some_path/', YourConsumer.as_asgi()),  # Make sure this matches the class in consumers.py
]
