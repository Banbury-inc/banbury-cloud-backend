from django.urls import path, include
from helloapp import consumers

urlpatterns = [
    path('', include('helloapp.urls')),
]

websocket_urlpatterns = [
    path('ws/some_path/', consumers.YourConsumer.as_asgi()),
]
