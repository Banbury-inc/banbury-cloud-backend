from django.urls import path, include
from websocket.urls import websocket_urlpatterns
from . import views

urlpatterns = [
    path("", views.homepage, name="home"),
    path('ws/', include(websocket_urlpatterns)),
    path('browserbase/', include('apps.browserbase.urls')),
    path('billing/', include('apps.billing.urls')),
]
