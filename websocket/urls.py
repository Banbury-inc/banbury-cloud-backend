from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/live_data/$', consumers.Live_Data.as_asgi()),
    re_path(r'ws/download_request/$', consumers.Download_File_Request.as_asgi()),
]
