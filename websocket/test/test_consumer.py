from django.test import TestCase, override_settings
from channels.testing import WebsocketCommunicator
from channels.routing import URLRouter
from django.urls import re_path
from ..consumers import Consumer
from unittest.mock import patch, MagicMock
import json

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

    @override_settings(ALLOWED_HOSTS=['api.dev.banbury.io'])
    async def test_consumer_receive_message(self):
        """Test that a websocket can receive messages and process them"""
        # Create an application with our websocket URL routing
        application = URLRouter([
            re_path(r'ws/consumer/(?P<device_id>[^/]+)/$', Consumer.as_asgi()),
        ])
        
        # Mock the necessary functions
        with patch('apps.devices.declare_device_online_with_id') as mock_device_online, \
             patch('apps.devices.get_single_device_info') as mock_device_info, \
             patch('apps.devices.declare_user_online') as mock_user_online, \
             patch('django.contrib.sites.shortcuts.get_current_site', return_value=type('Site', (), {'domain': 'api.dev.banbury.io'})), \
             patch('websocket.consumers.Consumer.process_update') as mock_process_update:
            
            # Set up mock returns
            mock_device_online.return_value = True
            mock_device_info.return_value = {
                'device_info': {
                    'user_id': '6756092e76ebec5a4ac8cd09'
                }
            }
            mock_user_online.return_value = True
            mock_process_update.return_value = None
            
            # Connect to the websocket
            communicator = WebsocketCommunicator(
                application=application,
                path='ws://api.dev.banbury.io/ws/consumer/6756092e76ebec5a4ac8cd09/'
            )
            connected, _ = await communicator.connect()
            self.assertTrue(connected)
            
            # Test sending a message
            test_message = {
                'type': 'update',
                'content': 'test content'
            }
            await communicator.send_json_to(test_message)
            
            # Verify that process_update was called with the message
            mock_process_update.assert_called_once_with(test_message)
            
            # Clean up
            await communicator.disconnect()

    @override_settings(ALLOWED_HOSTS=['api.dev.banbury.io'])
    async def test_consumer_disconnect(self):
        """Test that a websocket properly handles disconnection"""
        # Create an application with our websocket URL routing
        application = URLRouter([
            re_path(r'ws/consumer/(?P<device_id>[^/]+)/$', Consumer.as_asgi()),
        ])
        
        # Mock the necessary functions
        with patch('apps.devices.declare_device_online_with_id') as mock_device_online, \
             patch('apps.devices.get_single_device_info') as mock_device_info, \
             patch('apps.devices.declare_user_online') as mock_user_online, \
             patch('apps.devices.declare_device_offline_with_id') as mock_device_offline, \
             patch('apps.devices.declare_user_offline') as mock_user_offline, \
             patch('django.contrib.sites.shortcuts.get_current_site', return_value=type('Site', (), {'domain': 'api.dev.banbury.io'})):
            
            # Set up mock returns
            device_id = '6756092e76ebec5a4ac8cd09'
            user_id = '6756092e76ebec5a4ac8cd10'
            mock_device_online.return_value = True
            mock_device_info.return_value = {
                'device_info': {
                    'user_id': user_id
                }
            }
            mock_user_online.return_value = True
            mock_device_offline.return_value = True
            mock_user_offline.return_value = True
            
            # Connect to the websocket
            communicator = WebsocketCommunicator(
                application=application,
                path=f'ws://api.dev.banbury.io/ws/consumer/{device_id}/'
            )
            connected, _ = await communicator.connect()
            self.assertTrue(connected)
            
            # Disconnect and verify that the offline functions are called
            await communicator.disconnect()
            
            # Verify offline calls
            mock_device_offline.assert_called_once_with(device_id)
            mock_user_offline.assert_called_once_with(user_id)

    @override_settings(ALLOWED_HOSTS=['api.dev.banbury.io'])
    async def test_consumer_broadcast_message(self):
        """Test that a websocket can broadcast messages to a client"""
        # Create an application with our websocket URL routing
        application = URLRouter([
            re_path(r'ws/consumer/(?P<device_id>[^/]+)/$', Consumer.as_asgi()),
        ])
        
        # Mock the necessary functions
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
            
            # Connect to the websocket
            communicator = WebsocketCommunicator(
                application=application,
                path='ws://api.dev.banbury.io/ws/consumer/6756092e76ebec5a4ac8cd09/'
            )
            connected, _ = await communicator.connect()
            self.assertTrue(connected)
            
            # Test receiving a broadcast message
            test_message = {
                'type': 'broadcast_message',
                'message': {
                    'event': 'file_update',
                    'data': {'file_id': '12345', 'status': 'updated'}
                }
            }
            
            # Simulate the consumer getting a message from a channel layer
            # This is a bit of a hack because we're directly accessing the instance method
            # Normally this would be triggered by the channel layer
            consumer = communicator.application
            await consumer.broadcast_message(test_message)
            
            # Check that we received the message
            response = await communicator.receive_json_from()
            self.assertEqual(response['event'], 'file_update')
            self.assertEqual(response['data']['file_id'], '12345')
            self.assertEqual(response['data']['status'], 'updated')
            
            # Clean up
            await communicator.disconnect() 
