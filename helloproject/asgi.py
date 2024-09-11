"""
ASGI config for helloproject project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/howto/deployment/asgi/
"""

import os

from channels.routing import ProtocolTypeRouter
from channels.auth import AuthMiddlewareStack
from channels.routing import URLRouter
from django.core.asgi import get_asgi_application
import helloapp.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'helloproject.settings')

# application = get_asgi_application()

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            helloapp.routing.websocket_urlpatterns
        )
    ),
})
