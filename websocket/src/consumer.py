import json
from channels.generic.websocket import AsyncWebsocketConsumer

from .handle_device_info_response import handle_device_info_response
from .handle_direct_message import handle_direct_message
from .handle_download_request import handle_download_request
from .handle_file_sent_successfully import handle_file_sent_successfully
from .handle_file_transfer_complete import handle_file_transfer_complete
from .handle_initiate_live_data_connection import handle_initiate_live_data_connection
from .handle_start_file_transfer import handle_start_file_transfer
from .handle_file_chunk import handle_file_chunk


class Consumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        print('WebSocket connection accepted.')
        
        # Initialize attributes for file transfer
        self.transfer_room = None
        self.active_transfer_rooms = set()
        self.device_id = None
        
        # Initialize in scope too for redundancy
        self.scope['transfer_room'] = None
        self.scope['transfer_rooms'] = set()
        self.scope['device_id'] = None
        
        print('Initialized file transfer tracking attributes')

    async def disconnect(self, close_code):
        print('WebSocket disconnected with code:', close_code)
        
        # Clean up transfer rooms
        if hasattr(self, 'active_transfer_rooms') and self.active_transfer_rooms:
            for room in self.active_transfer_rooms:
                print(f"👋 LEAVING TRANSFER ROOM: {room} due to disconnect")
                await self.channel_layer.group_discard(room, self.channel_name)
            print(f"👋 Left {len(self.active_transfer_rooms)} transfer rooms during disconnect")
            self.active_transfer_rooms.clear()

    async def receive(self, text_data=None, bytes_data=None):
        # First log what type of data we received
        if bytes_data:
            print(f"=== BINARY DATA RECEIVED ===")
            print(f"Received binary data of length: {len(bytes_data)} bytes")
            print(f"Current transfer room: {self.transfer_room}")
            print(f"Active transfer rooms: {self.active_transfer_rooms}")
            
            try:
                await handle_file_chunk(self, bytes_data)
                print("Completed handling file chunk")
            except Exception as e:
                print(f"Error handling binary chunk: {str(e)}")
                # Try direct send as fallback
                try:
                    await self.send(bytes_data=bytes_data)
                    print(f"Fallback: Directly sent {len(bytes_data)} bytes to the client")
                except Exception as send_error:
                    print(f"Error in fallback send: {str(send_error)}")
                
        elif text_data:
            try:
                data = json.loads(text_data)
                print('Received text message:', data)
                message_type = data.get('message_type', '')
                
                # Handle leave_transfer_room message type
                if message_type == 'leave_transfer_room':
                    transfer_room = data.get('transfer_room')
                    if transfer_room:
                        print(f"👋 LEAVING TRANSFER ROOM: {transfer_room} due to explicit request")
                        
                        # Leave the room
                        await self.channel_layer.group_discard(transfer_room, self.channel_name)
                        
                        # Update tracking
                        if hasattr(self, 'active_transfer_rooms'):
                            self.active_transfer_rooms.discard(transfer_room)
                        if self.transfer_room == transfer_room:
                            self.transfer_room = None
                        
                        # Update scope
                        if self.scope.get('transfer_rooms'):
                            self.scope['transfer_rooms'].discard(transfer_room)
                        if self.scope.get('transfer_room') == transfer_room:
                            self.scope['transfer_room'] = None
                        
                        # Send confirmation
                        await self.send(text_data=json.dumps({
                            "type": "left_transfer_room",
                            "transfer_room": transfer_room,
                            "timestamp": data.get('timestamp', 0)
                        }))
                        return
                
                # Handle join_transfer_room message type specifically
                if message_type == 'join_transfer_room':
                    transfer_room = data.get('transfer_room')
                    if transfer_room:
                        # Store the transfer room for future binary messages
                        self.transfer_room = transfer_room
                        if not hasattr(self, 'active_transfer_rooms'):
                            self.active_transfer_rooms = set()
                        self.active_transfer_rooms.add(transfer_room)
                        
                        # Store in scope too
                        self.scope['transfer_room'] = transfer_room
                        if not self.scope.get('transfer_rooms'):
                            self.scope['transfer_rooms'] = set()
                        self.scope['transfer_rooms'].add(transfer_room)
                        
                        # Join the room
                        await self.channel_layer.group_add(transfer_room, self.channel_name)
                        print(f"Joined transfer room: {transfer_room}")
                        
                        # Send confirmation
                        await self.send(text_data=json.dumps({
                            "type": "transfer_room_joined",
                            "transfer_room": transfer_room,
                            "success": True
                        }))
                        return
                
                if message_type == 'initiate_live_data_connection':
                    await handle_initiate_live_data_connection(self, data)
                elif message_type == 'download_request':
                    await handle_download_request(self, data)
                elif message_type == 'file_transfer_complete':
                    await handle_file_transfer_complete(self, data)
                elif message_type == 'file_sent_successfully':
                    await handle_file_sent_successfully(self, data)
                elif message_type == 'file_start_transfer' or message_type == 'file_transfer_start' or message_type == 'start_file_transfer':
                    await handle_start_file_transfer(self, data)
                    
                    # If we have a transfer_room in the data, store it
                    if data.get('transfer_room'):
                        self.transfer_room = data.get('transfer_room')
                        if not hasattr(self, 'active_transfer_rooms'):
                            self.active_transfer_rooms = set()
                        self.active_transfer_rooms.add(self.transfer_room)
                        print(f"Stored transfer room from file_transfer_start: {self.transfer_room}")
                else:
                    print('Unhandled message type:', message_type)
            except Exception as e:
                print('Error processing text message:', e)
    
    async def forward_file_chunk(self, event):
        """
        Receive a forwarded binary file chunk event and send it to the client.
        """
        bytes_data = event.get('bytes_data')
        if bytes_data:
            print(f"Forwarding binary chunk of {len(bytes_data)} bytes to client")
            await self.send(bytes_data=bytes_data)
            print(f"Successfully forwarded {len(bytes_data)} bytes to client") 