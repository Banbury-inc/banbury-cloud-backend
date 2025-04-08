import json
from django.test import TestCase, override_settings
from channels.testing import WebsocketCommunicator
from channels.routing import URLRouter
from django.urls import re_path
from ..consumers import Consumer
from unittest.mock import patch

class TestWebsocketConsumer(TestCase):

    @override_settings(ALLOWED_HOSTS=['api.dev.banbury.io'])
    async def test_consumer_connect_dev(self):
        """Test that a websocket connection can be established with the dev URL"""
        # Create an application with our websocket URL routing
        application = URLRouter([
            re_path(r'ws/consumer/(?P<device_id>[^/]+)/$', Consumer.as_asgi()),
        ])
        
        # Mock the device and user-related functions
        with patch('apps.devices.declare_device_online_with_id') as mock_device_online, \
             patch('apps.devices.get_single_device_info') as mock_device_info, \
             patch('apps.devices.declare_user_online') as mock_user_online, \
             patch('django.contrib.sites.shortcuts.get_current_site', return_value=type('Site', (), {'domain': 'api.dev.banbury.io'})):
            
            # Set up mock returns
            mock_device_online.return_value = True
            mock_device_info.return_value = {
                'device_info': {
                    'user_id': '6756092e76ebec5a4ac8cd09'
                }
            }
            mock_user_online.return_value = True
            
            # Connect to the websocket with dev URL
            communicator = WebsocketCommunicator(
                application=application,
                path='ws://api.dev.banbury.io/ws/consumer/6756092e76ebec5a4ac8cd09/'
            )
            connected, _ = await communicator.connect()
            
            # Test that the connection was successful
            self.assertTrue(connected)
            
            # Test disconnection
            await communicator.disconnect() 