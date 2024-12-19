from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'live_data/$', consumers.Live_Data.as_asgi()),
    re_path(r'download_request/$', consumers.Download_File_Request.as_asgi()),
]
