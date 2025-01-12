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
            
        # Initialize active_groups set
        self.active_groups = set([f"device_{self.device_id}"])
        
        await self.channel_layer.group_add(
            f"device_{self.device_id}",
            self.channel_name
        )
        await self.accept()
        print(f"Connected to device {self.device_id}")

    async def disconnect(self, close_code):
        try:
            # Send disconnect message before closing
            await self.send(text_data=json.dumps({
                "type": "disconnect",
                "code": close_code,
                "reason": self.get_close_reason(close_code),
                "should_reconnect": self.should_attempt_reconnect(close_code)
            }))
        except Exception as e:
            print(f"Error sending disconnect message: {e}")

        # Remove from all active groups
        for group in self.active_groups:
            await self.channel_layer.group_discard(
                group,
                self.channel_name
            )
        self.active_groups.clear()
        print(f"Disconnected from device {self.device_id} with code {close_code}")

    def get_close_reason(self, code):
        """Map close codes to human-readable reasons"""
        reasons = {
            1000: "Normal closure",
            1001: "Going away",
            1006: "Abnormal closure",
            1011: "Internal server error",
            1012: "Service restart",
            1013: "Try again later"
        }
        return reasons.get(code, "Unknown reason")

    def should_attempt_reconnect(self, code):
        """Determine if client should attempt to reconnect based on close code"""
        # Codes where reconnection should be attempted
        reconnect_codes = {1001, 1006, 1012, 1013}
        return code in reconnect_codes

    async def receive(self, text_data=None, bytes_data=None):
        if text_data:
            await self.handle_text_data(text_data)
        elif bytes_data is not None and isinstance(bytes_data, (bytes, bytearray)):
            print("Received bytes data")
            await self.handle_bytes_data(bytes_data)
        else:
            print("No data received")


    async def handle_text_data(self, data):
        print(f"Received text data: {data}")
        data = json.loads(data)
        message_type = data.get("message_type")
        print(f"Message type: {message_type}")

        if message_type == "join_transfer_room":
            transfer_room = data.get("transfer_room")
            if transfer_room:
                print(f"Adding {self.channel_name} to transfer room: {transfer_room}")
                await self.channel_layer.group_add(
                    transfer_room,
                    self.channel_name
                )
                # Add to our tracked groups
                self.active_groups.add(transfer_room)
                print(f"Successfully added to transfer room: {transfer_room}")
                print(f"Current active groups: {self.active_groups}")
                # Send confirmation back to client
                await self.send(text_data=json.dumps({
                    "type": "transfer_room_joined",
                    "transfer_room": transfer_room,
                    "success": True
                }))
        elif message_type == "start_file_transfer":
            # Add handling for start_file_transfer message
            transfer_room = data.get("transfer_room")
            if transfer_room and transfer_room not in self.active_groups:
                await self.channel_layer.group_add(
                    transfer_room,
                    self.channel_name
                )
                self.active_groups.add(transfer_room)
                print(f"Added to transfer room during start_file_transfer: {transfer_room}")
                print(f"Current active groups: {self.active_groups}")
        elif message_type == "initiate_live_data_connection":
            await handle_initiate_live_data_connection(self, data)
        elif message_type == "device_info_response":
            await handle_device_info_response(data)
        elif message_type == "download_request":
            await handle_download_request(self, data)
        elif message_type == "file_sent_successfully":
            transfer_room = data.get("transfer_room", f"transfer_{data['sending_device_id']}_{data['requesting_device_id']}")
            # Make sure we're in the transfer room before sending
            if transfer_room not in self.active_groups:
                await self.channel_layer.group_add(
                    transfer_room,
                    self.channel_name
                )
                self.active_groups.add(transfer_room)
            
            await self.channel_layer.group_send(
                transfer_room,
                {
                    "type": "file_transfer_complete",
                    "message": "File transfer completed successfully",
                    "file_name": data.get("file_name"),
                    "requesting_device_id": data.get("requesting_device_id"),
                    "sending_device_id": data.get("sending_device_id"),
                    "sending_device_name": data.get("sending_device_name"),
                    "file_path": data.get("file_path"),
                    "transfer_room": transfer_room  # Include transfer room in response
                }
            )
        elif message_type == "file_transfer_complete":
            await handle_file_transfer_complete(self, data)
        elif message_type == "file_transaction_complete":
            await handle_file_transfer_complete(self, data)
        elif message_type == "direct_message":
            print("Received direct message")
            await handle_direct_message(self, data)
        elif message_type == "dm_event":
            await handle_direct_message(self, data)
        else:
            print(f"Received unrecognized message: {message_type}")
    
    async def handle_bytes_data(self, data):
        """Handle incoming bytes data"""
        print(f"Received bytes data length: {len(data)}")
        print(f"Active groups: {self.active_groups}")
        print(f"Channel name: {self.channel_name}")
        
        # Use active_groups instead of self.groups
        transfer_rooms = [group for group in self.active_groups if group.startswith("transfer_")]
        print(f"Found transfer rooms: {transfer_rooms}")
        
        if transfer_rooms:
            for room in transfer_rooms:
                print(f"Broadcasting bytes to room: {room}")
                try:
                    await self.channel_layer.group_send(
                        room,
                        {
                            "type": "bytes_transfer",
                            "bytes_data": data,
                            "sender": self.channel_name
                        }
                    )
                    print(f"Successfully sent bytes to room {room}")
                except Exception as e:
                    print(f"Error sending bytes to room {room}: {str(e)}")
        else:
            print(f"No transfer rooms found in active_groups: {self.active_groups}")
            await self.send(bytes_data=data)

    async def dm_event(self, event):
        """Handle incoming direct messages"""
        print(f"Received direct message: {event}")
        await self.send(text_data=json.dumps({
            "type": "direct_message",
            "message": event["message"],
            "requesting_device_id": event.get("requesting_device_id"),
            "sending_device_id": event.get("sending_device_id"),
            "file_name": event.get("file_name")
        }))

    async def file_request_event(self, event):
        """Handle incoming file requests"""
        # Add the sending device to the transfer room
        if "transfer_room" in event:
            await self.channel_layer.group_add(
                event["transfer_room"],
                self.channel_name
            )
            
        await self.send(text_data=json.dumps({
            "request_type": "file_request",
            "message": "file_request",
            "file_name": event["file_name"],
            "file_path": event.get("file_path"),
            "requesting_device_id": event["requesting_device_id"],
            "transfer_room": event.get("transfer_room"),  # Include in response
            "timestamp": event["timestamp"]
        }))

    async def bytes_transfer(self, event):
        """Handle incoming bytes transfer events"""
        # Don't send back to the sender
        if event.get('sender') != self.channel_name:
            print(f"Sending bytes to channel {self.channel_name}")
            await self.send(bytes_data=event["bytes_data"])
        else:
            print(f"Skipping bytes send to original sender {self.channel_name}")

    async def file_transfer_complete(self, event):
        """Handle file transfer complete notification"""
        await self.send(text_data=json.dumps({
            "type": "file_sent_successfully",
            "message": event["message"],
            "file_name": event["file_name"],
            "requesting_device_id": event["requesting_device_id"],
            "sending_device_id": event["sending_device_id"],
            "sending_device_name": event.get("sending_device_name"),
            "file_path": event.get("file_path")
        }))

