import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from .src.handle_device_info_response import handle_device_info_response
from .src.handle_download_request import handle_download_request
from .src.handle_file_sent_successfully import handle_file_sent_successfully
from .src.handle_initiate_live_data_connection import handle_initiate_live_data_connection
from .src.handle_file_transfer_complete import handle_file_transfer_complete
from .src.handle_direct_message import handle_direct_message
def device_group_name(device_id):
    """Generate the group name for a particular device."""
    return f"device_{device_id}"


class Consumer(AsyncWebsocketConsumer):
    async def connect(self):
        
        # Get device_id from URL parameters
        self.device_id = self.scope['url_route']['kwargs'].get('device_id')
        if not self.device_id:
            print("No device ID found")
            await self.close()
            return
            
        await self.channel_layer.group_add(
            f"device_{self.device_id}",
            self.channel_name
        )
        await self.accept()
        print(f"Connected to device {self.device_id}")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            device_group_name(self.device_id),
            self.channel_name
        )
        print(f"Disconnected from device {self.device_id}")

    async def receive(self, text_data=None, bytes_data=None):
        if text_data:
            await self.handle_text_data(text_data)
        elif bytes_data:
            await self.handle_bytes_data(bytes_data)
        else:
            print("No data received")


    async def handle_text_data(self, data):
        print(f"Received text data: {data}")
        data = json.loads(data)
        message_type = data.get("message_type")
        print(f"Message type: {message_type}")

        if message_type == "initiate_live_data_connection":
            await handle_initiate_live_data_connection(self, data)
        elif message_type == "device_info_response":
            await handle_device_info_response(data)
        elif message_type == "download_request":
            await handle_download_request(data)
        elif message_type == "file_sent_successfully":
            await handle_file_sent_successfully(data)
        elif message_type == "file_transfer_complete":
            await handle_file_transfer_complete(data)
        elif message_type == "file_transaction_complete":
            await handle_file_transfer_complete(data)
        elif message_type == "direct_message":
            print("Received direct message")
            await handle_direct_message(self, data)
        elif message_type == "dm_event":
            await handle_direct_message(self, data)
        else:
            print(f"Received unrecognized message: {message_type}")
    
    async def handle_bytes_data(self, data):
        print(f"Received bytes data: {data}")

    async def dm_event(self, event):
        """Handle incoming direct messages"""
        await self.send(text_data=json.dumps({
            "type": "direct_message",
            "message": event["message"],
            "sender_id": event["sender_id"]
        }))