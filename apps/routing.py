
from django.urls import path
from helloapp.consumers import Download_File_Request, Live_Data  # Make sure this matches the actual name

websocket_urlpatterns = [
    path('ws/live_data/', Live_Data.as_asgi()),  # Make sure this matches the class in consumers.py
    path('ws/download_request/', Download_File_Request.as_asgi()),  # Make sure this matches the class in consumers.py
]
