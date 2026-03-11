from django.urls import re_path
from . import consumers
from apps.meeting_agent.consumers import TranscriptionConsumer
from apps.terminal.consumers import TerminalConsumer

websocket_urlpatterns = [
    re_path(r'ws/consumer/(?P<device_id>[^/]+)/$', consumers.Consumer.as_asgi()),
    re_path(r'ws/transcription/(?P<session_id>[^/]+)/$', TranscriptionConsumer.as_asgi()),
    re_path(r'ws/terminal/(?P<session_id>[^/]+)/$', TerminalConsumer.as_asgi()),
]
