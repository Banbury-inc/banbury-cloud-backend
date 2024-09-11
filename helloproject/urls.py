from django.urls import path, include
from helloapp import consumers

urlpatterns = [
    path('', include('helloapp.urls')),
]

websocket_urlpatterns = [
    path('ws/live_data/', consumers.Live_Data.as_asgi()),
    path('ws/download_request/', consumers.Download_File_Request.as_asgi()),
]
