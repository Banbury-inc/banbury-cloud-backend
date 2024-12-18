from django.urls import path, include

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

websocket_urlpatterns = [
    path('', include('websocket.urls')),
]
