import json
from bson.objectid import ObjectId
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from .src.handle_device_info_response import handle_device_info_response
from .src.handle_download_request import handle_download_request
from .src.handle_file_sent_successfully import handle_file_sent_successfully
from .src.handle_initiate_live_data_connection import handle_initiate_live_data_connection
from .src.handle_file_transfer_complete import handle_file_transfer_complete
from .src.handle_direct_message import handle_direct_message
from apps.devices.declare_device_online_with_id import declare_device_online_with_id
from apps.devices.declare_device_offline_with_id import declare_device_offline_with_id
from apps.devices.get_single_device_info import get_single_device_info
from apps.devices.declare_user_online import declare_user_online
from apps.devices.declare_user_offline import declare_user_offline
from apps.devices.get_user_info import get_user_info
from apps.devices.get_device_info import get_device_info
from apps.notifications.get_notifications import get_notifications as db_get_notifications
import asyncio

def device_group_name(device_id):
    """Generate the group name for a particular device."""
    return f"device_{device_id}"


class Consumer(AsyncWebsocketConsumer):
    # Class-level tracking
    active_transfer_rooms = set()
    active_connections = {}  # device_id -> connection mapping
    tasks = {}  # Store tasks by connection
    TASK_SHUTDOWN_TIMEOUT = 300  # 5 minutes timeout for task shutdown

    async def connect(self):
        # Get device_id from URL parameters
        self.device_id = self.scope['url_route']['kwargs'].get('device_id')
        if not self.device_id:
            print("No device ID found")
            await self.close()
            return

        # Initialize tasks set for this connection
        self.tasks[self.channel_name] = set()
        
        # Check for existing connection
        existing_connection = self.active_connections.get(self.device_id)
        if existing_connection and existing_connection != self:
            print(f"Closing existing connection for device {self.device_id}")
            try:
                # Cancel all tasks for the existing connection with extended timeout
                if existing_connection.channel_name in self.tasks:
                    await self.cleanup_tasks(existing_connection.channel_name)
                await existing_connection.close(code=1000)
            except Exception as e:
                print(f"Error closing existing connection: {e}")

        # Store this connection
        self.active_connections[self.device_id] = self
            
        # Initialize active_groups set
        self.active_groups = set([f"device_{self.device_id}"])
        
        await self.channel_layer.group_add(
            f"device_{self.device_id}",
            self.channel_name
        )
        await self.accept()
        print(f"Connected to device {self.device_id}")

        # Declare device online only if this is the active connection
        if self.active_connections.get(self.device_id) == self:
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

    async def cleanup_tasks(self, channel_name: str):
        """Clean up tasks with extended timeout"""
        if channel_name in self.tasks:
            try:
                # Create a list of tasks to clean up
                tasks_to_cleanup = list(self.tasks[channel_name])
                
                # Cancel all tasks
                for task in tasks_to_cleanup:
                    if not task.done():
                        task.cancel()
                
                if tasks_to_cleanup:
                    # Wait for all tasks to complete or timeout
                    try:
                        await asyncio.wait(
                            tasks_to_cleanup,
                            timeout=self.TASK_SHUTDOWN_TIMEOUT
                        )
                    except asyncio.TimeoutError:
                        print(f"Timeout waiting for tasks to cleanup for channel {channel_name}")
                    
                # Clear and remove the tasks set
                self.tasks[channel_name].clear()
                del self.tasks[channel_name]
                
            except Exception as e:
                print(f"Error during task cleanup: {e}")

    async def disconnect(self, close_code):
        try:
            # Cancel all tasks associated with this connection with extended timeout
            await self.cleanup_tasks(self.channel_name)

            # Only send disconnect message if this was the active connection
            if self.active_connections.get(self.device_id) == self:
                try:
                    await asyncio.wait_for(
                        self.send(text_data=json.dumps({
                            "type": "disconnect",
                            "code": close_code,
                            "reason": self.get_close_reason(close_code),
                            "should_reconnect": self.should_attempt_reconnect(close_code)
                        })),
                        timeout=5.0  # 5 second timeout for sending disconnect message
                    )
                except Exception as e:
                    print(f"Error sending disconnect message: {e}")

                # Remove from connection tracking
                self.active_connections.pop(self.device_id, None)

                # Remove from all active groups with extended timeout
                group_removal_tasks = []
                for group in self.active_groups:
                    try:
                        task = asyncio.create_task(
                            self.channel_layer.group_discard(group, self.channel_name)
                        )
                        group_removal_tasks.append(task)
                    except Exception as e:
                        print(f"Error creating group removal task for {group}: {e}")

                if group_removal_tasks:
                    try:
                        await asyncio.wait(
                            group_removal_tasks,
                            timeout=self.TASK_SHUTDOWN_TIMEOUT
                        )
                    except asyncio.TimeoutError:
                        print("Timeout removing from groups")
                    except Exception as e:
                        print(f"Error during group removal: {e}")

                self.active_groups.clear()

                print(f"Disconnected from device {self.device_id} with code {close_code}")

                # Only declare offline if this was the active connection
                result = declare_device_offline_with_id(self.device_id)
                print(f"[WebSocket] Device offline declaration result: {result}")

                device_info = await sync_to_async(get_single_device_info)(self.device_id)
                user_id = device_info.get('device_info', {}).get('user_id')
                if user_id:
                    user_info = await sync_to_async(get_user_info)(user_id)
                    username = user_info.get('username')
                    devices_info = await sync_to_async(get_device_info)(username)
                    
                    # Check if all devices are offline
                    all_devices_offline = True
                    for device in devices_info.get('devices', []):
                        if device.get('online') == True and device.get('_id') != self.device_id:
                            all_devices_offline = False
                            break
                            
                    if all_devices_offline:
                        result = declare_user_offline(user_id)
                        print(f"[WebSocket] User offline declaration result: {result}")

        except Exception as e:
            print(f"Error during disconnect: {e}")

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
        # Only reconnect for abnormal closures and service restarts
        reconnect_codes = {1006, 1012, 1013}
        return code in reconnect_codes

    async def receive(self, text_data=None, bytes_data=None):
        try:
            if text_data:
                # Create a task for handling text data
                task = asyncio.create_task(self.handle_text_data(text_data))
                
                # Only add to tasks if the channel still exists
                if self.channel_name in self.tasks:
                    self.tasks[self.channel_name].add(task)
                    task.add_done_callback(
                        lambda t: self.tasks.get(self.channel_name, set()).discard(t)
                        if self.channel_name in self.tasks else None
                    )
                
                await asyncio.wait_for(task, timeout=self.TASK_SHUTDOWN_TIMEOUT)
                
            elif bytes_data is not None and isinstance(bytes_data, (bytes, bytearray)):
                # Create a task for handling bytes data
                task = asyncio.create_task(self.handle_bytes_data(bytes_data))
                
                # Only add to tasks if the channel still exists
                if self.channel_name in self.tasks:
                    self.tasks[self.channel_name].add(task)
                    task.add_done_callback(
                        lambda t: self.tasks.get(self.channel_name, set()).discard(t)
                        if self.channel_name in self.tasks else None
                    )
                
                await asyncio.wait_for(task, timeout=self.TASK_SHUTDOWN_TIMEOUT)
            else:
                print("No data received")
        except asyncio.TimeoutError:
            print("Message handling timed out")
        except Exception as e:
            print(f"Error handling message: {e}")

    async def handle_text_data(self, data):
        print(f"Received text data: {data}")
        data = json.loads(data)
        message_type = data.get("type") or data.get("message_type")
        print(f"Message type: {message_type}")

        if message_type == "ping":
            # Respond to heartbeat
            await self.send(text_data=json.dumps({
                "type": "pong",
                "timestamp": data.get("timestamp")
            }))
            return

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
            print(f"Received unrecognized message: {message_type}")
    
    async def handle_bytes_data(self, data):
        """Handle incoming bytes data"""
        
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

