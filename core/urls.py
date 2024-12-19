from django.urls import path, include
from channels.routing import ProtocolTypeRouter, URLRouter
from websocket.urls import websocket_urlpatterns

urlpatterns = [
    path('', include('apps.urls')),
    path('authentication/', include('apps.authentication.urls')),
    path('devices/', include('apps.devices.urls')),
    path('files/', include('apps.files.urls')),
    path('predictions/', include('apps.predictions.urls')),
    path('profiles/', include('apps.profiles.urls')),
    path('sessions/', include('apps.sessions.urls')),
    path('settings/', include('apps.settings.urls')),
    path('tasks/', include('apps.tasks.urls')),
    path('users/', include('apps.users.urls')),
]

# Remove this as it's not needed for WebSocket routing
# websocket_urlpatterns = [
#     path('ws/', include('websocket.urls')),
# ]

# Instead, create an application routing configuration
application = ProtocolTypeRouter({
    "websocket": URLRouter(websocket_urlpatterns),
})
