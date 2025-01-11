from django.urls import re_path
from . import old_consumers
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/consumer/(?P<device_id>[^/]+)/$', consumers.Consumer.as_asgi()),
    re_path(r'ws/live_data/$', old_consumers.Live_Data.as_asgi()),
    re_path(r'ws/download_request/$', old_consumers.Download_File_Request.as_asgi()),
]
