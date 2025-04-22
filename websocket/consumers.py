import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from .src.handle_device_info_response import handle_device_info_response
from .src.handle_download_request import handle_download_request
from .src.handle_initiate_live_data_connection import handle_initiate_live_data_connection
from .src.handle_file_transfer_complete import handle_file_transfer_complete
from .src.handle_direct_message import handle_direct_message
from .src.handle_cancel_download_request import handle_cancel_download_request, cancel_transfer_event
from apps.devices.declare_device_online_with_id import declare_device_online_with_id
from apps.devices.declare_device_offline_with_id import declare_device_offline_with_id
from apps.devices.get_single_device_info import get_single_device_info
from apps.devices.declare_user_online import declare_user_online
from apps.devices.declare_user_offline import declare_user_offline
from apps.devices.get_user_info import get_user_info
from apps.devices.get_device_info import get_device_info


def device_group_name(device_id):
    """Generate the group name for a particular device."""
    return f"device_{device_id}"


class Consumer(AsyncWebsocketConsumer):
    # Class-level dictionary to track all transfer rooms
    active_transfer_rooms = set()

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

        result = declare_device_online_with_id(self.device_id)
        print(f"[WebSocket] Device online declaration result: {result}")

        # Get device info
        device_info = await sync_to_async(get_single_device_info)(self.device_id)
        # Add user to their personal notification group
        user_id = device_info.get('device_info', {}).get('user_id')
        print(f"[WebSocket] User ID: {user_id}")
        if user_id:
            print(f"User ID: {user_id}")
            # Add to user's personal notification group
            user_group = f"user_{user_id}"
            self.active_groups.add(user_group)
            await self.channel_layer.group_add(
                user_group,
                self.channel_name
            )
            result = declare_user_online(user_id)
            print(f"[WebSocket] User online declaration result: {result}")
            print(f"Added to {user_group}")

        print(f"Active groups: {self.active_groups}")

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

        result = declare_device_offline_with_id(self.device_id)
        print(f"[WebSocket] Device offline declaration result: {result}")
        device_info = await sync_to_async(get_single_device_info)(self.device_id)
        user_id = device_info.get('device_info', {}).get('user_id')
        if user_id:
            user_info = await sync_to_async(get_user_info)(user_id)
            username = user_info.get('username')
            devices_info = await sync_to_async(get_device_info)(username)

            # Initialize all_devices_offline flag
            all_devices_offline = True

            # Check online status from devices
            for device in devices_info.get('devices', []):
                if device.get('online') == True:
                    all_devices_offline = False
                    break

            if all_devices_offline:
                result = declare_user_offline(user_id)
                print(f"[WebSocket] User offline declaration result: {result}")

        # Remove from class-level tracking when disconnecting
        for group in self.active_groups:
            if group.startswith("transfer_"):
                Consumer.active_transfer_rooms.discard(group)

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
            await self.handle_bytes_data(bytes_data)
        else:
            print("No data received")

    async def handle_text_data(self, text_data):
        print(f"Received text data: {text_data}")
        data = json.loads(text_data)
        message_type = data.get("message_type")
        print(f"Message type: {message_type}")

        if message_type == "join_transfer_room":
            transfer_room = data.get("transfer_room")
            if transfer_room:
                print(f"Adding {self.channel_name} to transfer room: {transfer_room}")
                # Add to both instance and class-level tracking
                self.active_groups.add(transfer_room)
                Consumer.active_transfer_rooms.add(transfer_room)
                await self.channel_layer.group_add(
                    transfer_room,
                    self.channel_name
                )
                # Send confirmation back to client
                await self.send(text_data=json.dumps({
                    "type": "transfer_room_joined",
                    "transfer_room": transfer_room,
                    "success": True
                }))
                print(f"Current active groups: {self.active_groups}")
        elif message_type == "start_file_transfer":
            transfer_room = data.get("transfer_room")
            if transfer_room and transfer_room not in self.active_groups:
                await self.channel_layer.group_add(
                    transfer_room,
                    self.channel_name
                )
                self.active_groups.add(transfer_room)
                print(f"Added to transfer room during start_file_transfer: {transfer_room}")
                print(f"Current active groups: {self.active_groups}")
        elif message_type == "leave_transfer_room":
            transfer_room = data.get("transfer_room")
            if transfer_room:
                print(f"[Consumer] Handling leave_transfer_room for {self.channel_name} from room {transfer_room}")
                # Remove self from the group
                await self.channel_layer.group_discard(
                    transfer_room,
                    self.channel_name
                )
                # Update internal tracking
                self.active_groups.discard(transfer_room)
                Consumer.active_transfer_rooms.discard(transfer_room) # Also update class-level tracking
                print(f"[Consumer] Removed {self.channel_name} from group {transfer_room}. Active groups: {self.active_groups}")
                
                # Send confirmation back to the client who sent leave
                await self.send(text_data=json.dumps({
                    "type": "left_transfer_room", # Confirmation type
                    "transfer_room": transfer_room,
                    "success": True
                }))
                
                # Notify *other* members of the group that this user left
                await self.channel_layer.group_send(
                    transfer_room, # Send to the remaining members
                    {
                        "type": "transfer_participant_left", # Use a specific type for this notification
                        "transfer_room": transfer_room,
                        "leaving_channel": self.channel_name, # Inform who left
                        "timestamp": data.get("timestamp", 0) # Forward timestamp if available
                    }
                )
                print(f"[Consumer] Notified group {transfer_room} that {self.channel_name} left.")
            else:
                print("[Consumer] leave_transfer_room message missing transfer_room")
        elif message_type == "initiate_live_data_connection":
            await handle_initiate_live_data_connection(self, data)
        elif message_type == "device_info_response":
            await handle_device_info_response(data)
        elif message_type == "download_request":
            await handle_download_request(self, data)
        elif message_type == "cancel_download_request":
            await handle_cancel_download_request(self, data)
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
        elif message_type == "mark_notification_read":
            # After marking notification as read, send update to user's group
            user_id = data.get("user_id")
            if user_id:
                await self.channel_layer.group_send(
                    f"user_{user_id}",
                    {
                        "type": "notification_update",
                        "user_id": user_id
                    }
                )
        else:
            print(f"Received unrecognized message type: {message_type}")

    async def handle_bytes_data(self, data):
        """Handle incoming bytes data"""

        print(f"Received bytes data: {len(data)} bytes")

        # Use class-level tracking of transfer rooms
        transfer_rooms = [room for room in Consumer.active_transfer_rooms]

        if transfer_rooms:
            for room in transfer_rooms:
                try:
                    await self.channel_layer.group_send(
                        room,
                        {
                            "type": "bytes_transfer",
                            "bytes_data": data,
                            "sender": self.channel_name
                        }
                        )

                    print(f"Sent bytes data to room {room}: {len(data)} bytes")
                except Exception as e:
                    print(f"Error sending bytes to room {room}: {str(e)}")
        else:
            await self.send(bytes_data=data)

    async def dm_event(self, event):
        """Handle incoming direct messages"""
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
            await self.send(bytes_data=event["bytes_data"])

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

    async def friend_request(self, event):
        """Handle incoming friend requests"""
        await self.send(text_data=json.dumps(event["message"]))

    async def notification_update(self, event):
        """Handle notification updates"""
        # Get fresh notifications for the user
        user_id = event.get("user_id")
        if user_id:
            await self.send(text_data=json.dumps({
                "type": "notification_update",
            }))

    async def cancel_transfer_event(self, event):
        """
        Handler for the 'cancel_transfer_event' type sent via channel layers.
        This forwards the cancellation instruction to the specific consumer (sending device).
        """
        await cancel_transfer_event(self, event)

    # Add handler for the new group message type 'transfer_participant_left'
    async def transfer_participant_left(self, event):
        """Forwards the notification about a participant leaving a transfer room."""
        print(f"[Consumer] Forwarding transfer_participant_left event: {event}")
        await self.send(text_data=json.dumps({
            "type": "leave_transfer_room", # Match receiver expectation
            "transfer_room": event.get("transfer_room"),
            "reason": "participant_left",
            "leaving_channel": event.get("leaving_channel"),
            "timestamp": event.get("timestamp")
        }))
