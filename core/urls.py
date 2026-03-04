from django.urls import path, include
from websocket.urls import websocket_urlpatterns
from apps.health.views import HealthCheckView

urlpatterns = [
    path('', include('apps.urls')),
    path('authentication/', include('apps.authentication.urls')),
    path('conversations/', include('apps.conversations.urls')),
    path('devices/', include('apps.devices.urls')),
    path('docs/', include('apps.docs.urls')),
    path('files/', include('apps.files.urls')),
    path('predictions/', include('apps.predictions.urls')),
    path('sessions/', include('apps.sessions.urls')),
    path('settings/', include('apps.settings.urls')),
    path('tasks/', include('apps.tasks.urls')),
    path('users/', include('apps.users.urls')),
    path('notifications/', include('apps.notifications.urls')),
    path('analytics/', include('apps.analytics.urls')),
    path('databases/', include('apps.databases.urls')),
    path('meeting-agent/', include('apps.meeting_agent.urls')),
    path('flows/', include('apps.flows.urls')),
    path('ws/', include(websocket_urlpatterns)),
    path('health/', HealthCheckView.as_view(), name='health_check'),
]
