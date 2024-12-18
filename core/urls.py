from django.urls import path, include
from apps import consumers

urlpatterns = [
    path('', include('apps.urls')),
    path('authentication/', include('apps.authentication.urls')),
]

websocket_urlpatterns = [
    path('ws/live_data/', consumers.Live_Data.as_asgi()),
    path('ws/download_request/', consumers.Download_File_Request.as_asgi()),
]


