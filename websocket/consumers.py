import json
import os
import asyncio
from datetime import datetime
from channels.generic.websocket import AsyncWebsocketConsumer
from apps.files.search_for_file import search_for_file
from apps.devices.declare_device_offline import declare_device_offline
from apps.devices.declare_device_online import declare_device_online
from apps.devices.get_online_devices import get_online_devices
from apps.devices.process_device_info import process_device_info
from apps.predictions.pipeline import pipeline
from apps.predictions.get_download_queue import get_download_queue
from .utils import announce_connection
import time


# Change the connected_devices global to store both connection ID and WebSocket
connected_devices = {}  # Will store {device_name: {'connection_id': id, 'websocket': ws}}
websocket_connections = {}


class Live_Data(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)
        self.file_name = None
        self.device_info_task = None
        self.device_predictions_task = None
        self.device_name = None
        self.requesting_device_name = None
        self.run_device_info_loop = None
        self.run_device_predictions_loop = None
        self.should_run = True
        self.connection_id = id(self)

    async def connect(self):
        await self.accept()
        device_name = self.scope.get('requesting_device_name')
        username = self.scope.get('username')
        run_device_info_loop = self.scope.get('run_device_info_loop', True)
        run_device_predictions_loop = self.scope.get('run_device_predictions_loop', True)

        print("Device name: ", device_name)
        print("Username: ", username)
        print("Connection ID: ", self.connection_id)
        print("WebSocket: ", self)
        websocket_connections[self.connection_id] = self  # Using dict is better here since we have a unique connection_id
        print("Websocket connections: ", websocket_connections)


        
        if not device_name or not username:
            print("[WebSocket] Waiting for device identification...")
            return
        
        if device_name:
            # Check if device already has a connection and it's a different connection
            if device_name in connected_devices:
                existing_connection = connected_devices[device_name]['websocket']
                if existing_connection.connection_id != self.connection_id:
                    try:
                        # Close the old connection
                        await existing_connection.close()
                        print(f"Closed old connection for {device_name}")
                    except Exception as e:
                        print(f"Error closing old connection: {e}")
            
            # Update the connection in connected_devices with both ID and WebSocket
            self.device_name = device_name
            connected_devices[device_name] = {
                'connection_id': self.connection_id,
                'websocket': self
            }
            print(f"Added/Updated WebSocket connection for {device_name} with ID {self.connection_id}")

            try:
                result = declare_device_online(username, device_name)
                print(f"[WebSocket] Device online declaration result: {result}")
                
                if isinstance(result, dict) and result.get('result') == 'success':
                    await self.trigger_connect(username, device_name)
                    if run_device_info_loop:
                        await self.start_device_info_loop(username, device_name, run_device_info_loop)
                    if run_device_predictions_loop:
                        await self.start_device_predictions_loop(username, device_name, run_device_predictions_loop)
                else:
                    print(f"[WebSocket] Failed to set device online: {result}")
            except Exception as e:
                print(f"[WebSocket] Error during device connection: {str(e)}")

    async def disconnect(self, close_code):
        try:
            device_name = self.scope.get('requesting_device_name')
            username = self.scope.get('username')
            
            self.should_run = False
            
            if self.device_info_task:
                self.device_info_task.cancel()
                try:
                    await self.device_info_task
                except asyncio.CancelledError:
                    print(f"Device info loop for {device_name} has been cancelled.")
            
            if device_name in connected_devices:
                if connected_devices[device_name]['connection_id'] == self.connection_id:
                    connected_devices.pop(device_name)
                    print(f"Removed WebSocket connection for {device_name} with ID {self.connection_id}")
                    print(f"Remaining connected devices: {list(connected_devices.keys())}")

            if device_name and username:
                await self.trigger_post_disconnect(username, device_name)
                
        except Exception as e:
            print(f"Error disconnecting: {e}")

    async def announce_connection(self):
        print(f"Announcing connection for {self.device_name}")
        for connection_id, connection in websocket_connections.items():
            await connection.send(text_data=json.dumps({
                'message': f"Requesting file {file_name}",
                'request_type': 'file_request',
                'file_name': file_name,
                'requesting_device_name': requesting_device_name  # Use self.device_name for the requesting device
            }))

    async def announce_download_request(self):
        print(f"Announcing connection for {self.device_name}")
        for connection_id, connection in websocket_connections.items():
            await connection.send(text_data=json.dumps({
                'message': f"Requesting file",
                # 'request_type': 'file_request',
                'device_name': self.device_name,
                'connection_id': self.connection_id
            }))

    async def start_device_info_loop(self, username, device_name, run_device_info_loop):
        print(f"Inside start device info loop function for {device_name}")
        """Start a loop to periodically update device information."""
        if run_device_info_loop:
            try:
                # Create a task that can be tracked and cancelled
                self.device_info_task = asyncio.create_task(self._device_info_loop(username, device_name))
                # Give the task a name for easier tracking
                self.device_info_task.set_name(f"device_info_loop_{device_name}")
                # Don't await the task here - let it run independently
            except Exception as e:
                print(f"Error creating device info loop for {device_name}: {e}")
                self.should_run = False
        
    async def start_device_predictions_loop(self, username, device_name, run_device_predictions_loop):
        """Start a loop to periodically take that information and make preditctions."""
        if run_device_predictions_loop:
            try:
                # Create a task that can be tracked and cancelled
                self.device_predictions_task = asyncio.create_task(self._device_predictions_loop(username, device_name))
                # Give the task a name for easier tracking
                self.device_predictions_task.set_name(f"device_predictions_loop_{username}")
                # Don't await the task here - let it run independently
            except Exception as e:
                print(f"Error creating device predictions loop for {device_name}: {e}")
                self.should_run = False

    async def _device_info_loop(self, username, device_name):
        while self.should_run:
            print(f"Requesting device info for {device_name}")
            await self.request_device_info(username, device_name)
            await asyncio.sleep(600)  # Use asyncio.sleep instead of time.sleep


    async def _device_predictions_loop(self, username, device_name):
        while self.should_run:
            print(f"Making device predictions for {username}")
            await self.make_device_predictions(username, device_name)
            await asyncio.sleep(1800)  # Use asyncio.sleep instead of time.sleep

    async def request_device_info(self, username, device_name):
        """Request device information from the device."""
        await self.send(text_data=json.dumps({
            'message': "Requesting device information",
            'request_type': 'device_info'
        }))

    async def make_device_predictions(self, username, device_name):
        """Call pipeline"""
        print(f"Making device predictions for {username}")
        result = await pipeline(username)

        def convert_datetime(obj):
            """Recursively convert datetime objects to ISO format strings"""
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, dict):
                return {key: convert_datetime(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [convert_datetime(item) for item in list(obj)]
            return obj

        # Convert all datetime objects in the result
        result = convert_datetime(result)


        try:
            await self.send(text_data=json.dumps({
                'message': "File sync request",
                'download_queue': result,
                'request_type': 'file_sync_request',
            }))
            print("File sync request sent successfully")
        except Exception as e:
            print(f"Error sending file sync request: {str(e)}")

    async def trigger_connect(self, username, device_name):
        """Custom function to handle what happens after connect."""


        result = declare_device_online(username, device_name)
        print(f"Device online declaration result: {result}")


    async def trigger_post_disconnect(self, username, device_name):
        """Custom function to handle what happens after disconnect."""
        await declare_device_offline(username, device_name)

    async def receive(self, text_data=None, bytes_data=None):
        """Handle both text and binary data based on the type of the input."""
        
        # Check if the data is bytes (binary data)
        if bytes_data is not None and isinstance(bytes_data, (bytes, bytearray)):
            await self.receive_bytes(bytes_data)
        elif text_data is not None and isinstance(text_data, str):
            try:
                text_data_json = json.loads(text_data)

                # Handle device info response
                if text_data_json.get('message') == "device_info_response":
                    username = text_data_json.get('username')
                    sending_device_name = text_data_json.get('sending_device_name')
                    device_info = text_data_json.get('device_info')
                    
                    # Get requesting_device_name from scope if not in message
                    requesting_device_name = (
                        text_data_json.get('requesting_device_name') or 
                        self.scope.get('requesting_device_name')
                    )
                    
                    if all([username, sending_device_name, device_info]):
                        result = process_device_info(
                            username,
                            sending_device_name,
                            requesting_device_name,
                            device_info
                        )
                        
                        await self.send(text_data=json.dumps({
                            'message': 'Device info processed',
                            'status': result,
                            'device_name': sending_device_name
                        }))
                    else:
                        missing = []
                        if not username: missing.append('username')
                        if not sending_device_name: missing.append('sending_device_name')
                        if not device_info: missing.append('device_info')
                        await self.send(text_data=json.dumps({
                            'message': 'Error processing device info',
                            'error': f'Missing required fields: {", ".join(missing)}'
                        }))
                else:
                    # Handle all other messages
                    await self.receive_text(text_data)
            except json.JSONDecodeError:
                print("Error parsing JSON data.")
                await self.send(text_data=json.dumps({'error': "Invalid JSON format"}))

    async def receive_text(self, text_data):
        try:
            text_data_json = json.loads(text_data)

            # Move device identification logic to the beginning
            if 'username' in text_data_json:
                self.scope['username'] = text_data_json['username']

            if 'requesting_device_name' in text_data_json:
                device_name = text_data_json['requesting_device_name']
                self.scope['requesting_device_name'] = device_name
                self.device_name = device_name
                username = self.scope.get('username')
                
                # If we now have both username and device_name, declare device online
                if username and device_name:
                    connected_devices[device_name] = {
                        'connection_id': self.connection_id,
                        'websocket': self
                    }
                    result = declare_device_online(username, device_name)
                    print(f"[WebSocket] Device online declaration result: {result}")
                    
                    if isinstance(result, dict) and result.get('result') == 'success':
                        await self.trigger_connect(username, device_name)
                        await self.start_device_info_loop(username, device_name, self.run_device_info_loop)
                        await self.start_device_predictions_loop(username, device_name, self.run_device_predictions_loop)

            # Handle device info response
            if text_data_json.get('message') == "device_info_response":
                username = text_data_json.get('username')
                sending_device_name = text_data_json.get('sending_device_name')
                requesting_device_name = text_data_json.get('requesting_device_name')
                device_info = text_data_json.get('device_info')
                
                if all([username, sending_device_name, device_info]):
                    result = process_device_info(
                        username,
                        sending_device_name,
                        requesting_device_name,
                        device_info
                    )
                    
                    await self.send(text_data=json.dumps({
                        'message': 'Device info processed',
                        'status': result
                    }))
                else:
                    await self.send(text_data=json.dumps({
                        'message': 'Error processing device info',
                        'error': 'Missing required fields'
                    }))
                return  # Return after handling device info

            # Validate required fields
            if 'requesting_device_name' not in text_data_json:
                await self.send(text_data=json.dumps({
                    'message': 'Permission denied',
                    'error': "'requesting_device_name' not found"
                }))
                return

            # Add username to scope
            if 'username' in text_data_json:
                self.scope['username'] = text_data_json['username']

            if 'requesting_device_name' in text_data_json:
                self.scope['requesting_device_name'] = text_data_json['requesting_device_name']
                self.device_name = text_data_json['requesting_device_name']
                username = self.scope.get('username')
                if username:
                    await self.start_device_info_loop(username, self.device_name, self.run_device_info_loop)
                    await self.start_device_predictions_loop(username, self.device_name, self.run_device_predictions_loop)
                else:
                    print("Warning: Cannot start device info loop without username")
            
            username = self.scope.get('username')
            device_name = self.scope.get('requesting_device_name')

            if not username or not device_name:
                await self.send(text_data=json.dumps({
                    'message': 'Permission denied',
                    'error': "Missing username or device name"
                }))
                return

            if text_data_json.get('message') == "device_info_response":
                await self.send(text_data=json.dumps({
                    'message': 'Device info received',
                    'requesting_device_name': device_name,
                    'device_info': text_data_json.get('device_info')
                }))

            # Handle download request
            if text_data_json.get('message') == "Download Request":
                print("Download request received")
                if 'file_name' not in text_data_json:
                    await self.send(text_data=json.dumps({
                        'message': 'Transfer failed',
                        'error': "File name not provided"
                    }))
                    return

                self.file_name = text_data_json['file_name']
                print(f"self.file_name: ", self.file_name) 
                response = search_for_file(username, self.file_name)
                print(f"response: ", response)

                # Get device name directly from response since it's not nested
                sending_device_name = response.get('device_name')

                print(f"Sending device name: {sending_device_name}")

                if sending_device_name not in connected_devices:
                    await self.send(text_data=json.dumps({
                        'message': 'Device offline',
                        'sending_device_name': sending_device_name
                    }))
                    return
                else:
                    print("Device is online")
                    print(f"connected_devices: {connected_devices}")

                file_name = text_data_json['file_name']
                requesting_device_name = sending_device_name

                await announce_connection(websocket_connections, device_name, file_name, requesting_device_name)
                
                await self.announce_download_request()
                await self.announce_connection()

                for connection_id, connection in websocket_connections.items():
                    await connection.send(text_data=json.dumps({
                        'message': f"Requesting file {self.file_name}",
                        'request_type': 'file_request',
                        'file_name': self.file_name,
                        'requesting_device_name': self.device_name  # Use self.device_name for the requesting device
                    }))




            # Handle file transfer completion
            elif text_data_json.get('message') == "File sent successfully":
                print("File sent successfully")
                try:
                    # File handling logic...
                    await self.send(text_data=json.dumps({
                        'message': 'File transfer complete',
                        'file_name': self.file_name,
                        'requesting_device_name': text_data_json.get('requesting_device_name'),
                        'sending_device_name': text_data_json.get('sending_device_name')
                    }))
                except Exception as e:
                    await self.send(text_data=json.dumps({
                        'message': 'Transfer failed',
                        'error': str(e)
                    }))
            else:
                print(f"Received unrecognized message: {text_data_json.get('message')}")

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'message': 'Transfer failed',
                'error': "Invalid JSON format"
            }))
        except Exception as e:
            await self.send(text_data=json.dumps({
                'message': 'Transfer failed',
                'error': str(e)
            }))

    async def receive_bytes(self, bytes_data):
        # Save the file chunks to the 'files' directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_dir = os.path.join(current_dir, 'files')
        os.makedirs(file_dir, exist_ok=True)
        file_path = os.path.join(file_dir, "temporary_file_name")

        # Write the binary data to the file
        with open(file_path, 'ab') as f:
            f.write(bytes_data)

    async def finalize_file_transfer(self, file_name):
        """This function is called when file transfer is complete."""
        await self.send(text_data=json.dumps({
            'message': f"File {file_name} transfer completed."
        }))
        print(f"File {file_name} has been fully transferred.")

async def broadcast_new_file(new_file):
    for device_name, device_ws in connected_devices.items():
        await device_ws['websocket'].send(text_data=json.dumps({
            'message': f"New file {new_file} available for download."
        }))

    return "Broadcasted new file to all connected devices."
    
class Download_File_Request(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)
        self.file_name = None   

    async def connect(self):
        # Accept the WebSocket connection
        await self.accept()

    async def disconnect(self, close_code):
        # Handle WebSocket disconnection
        pass

    async def receive(self, text_data):
        # Receive data from WebSocket and process it
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        username = text_data_json['username']
        file_name = text_data_json['file_name']
        if file_name:
            self.scope['file_name'] = file_name
            self.file_name = file_name


        # Send 'Searching for file...' message
        response = "Searching for file..."
        await self.send(text_data=json.dumps({
            'message': response
        }))

        # Search for the file and the device that has it
        file_info = search_for_file(username, file_name)

        if file_info and 'file_data' in file_info:
            file_data = file_info['file_data']  # Extract the file_data dict

            # Extract the necessary file and device information
            file_name = file_data['file_name']
            device_name = file_data['device_name']  # The device that contains the file

            # Send 'Found file, requesting...' message
            response = f"Found file on {device_name}, requesting..."
            await self.send(text_data=json.dumps({
                'message': response,
                'request_type': 'update'
            }))


            # Look up the WebSocket connections for all connected devices
            if connected_devices:
                for device_name, device_ws in connected_devices.items():
                    file_name = self.scope.get("file_name")

                    # Send a request to each device WebSocket to check for the file
                    await device_ws['websocket'].send(text_data=json.dumps({
                        'message': f"Requesting file {file_name} from {device_name}",
                        'request_type': 'file_request',
                        'file_name': file_name
                    }))
            else:
                # No devices are connected
                response = "No devices are currently connected."
                await self.send(text_data=json.dumps({
                    'message': response
                }))

            # Look up the WebSocket connection for the device that contains the file
            if device_name in connected_devices:
                device_ws = connected_devices[device_name]
                file_name = self.scope.get("file_name")

                # Send a request to the device WebSocket to send the file
                await device_ws['websocket'].send(text_data=json.dumps({
                    'message': f"Requesting file {file_name} from {device_name}",
                    'request_type': 'file_request',
                    'file_name': file_name
                }))

                await device_ws['websocket'].send(text_data=json.dumps({
                    'message': f"Requesting file {file_name} from {device_name}",
                    'request_type': 'file_request',
                    'file_name': file_name
                }))

                # Notify the client that the request has been sent to the device
                response = "Request sent to device to retrieve the file"
                await self.send(text_data=json.dumps({
                    'message': response,
                    'request_type': 'update'
                }))
            else:
                # The device is not connected
                response = f"Device {device_name} is not connected."
                await self.send(text_data=json.dumps({
                    'message': response
                }))
        else:
            # If file not found
            response = f"File not found. File info: {file_info}"
            await self.send(text_data=json.dumps({
                'message': response
            }))

        # After file transfer is complete
        await self.send(text_data=json.dumps({
            'message': "File transfer complete",
            'status': 'download_complete',
            'file_name': file_name
        }))

    async def receive_bytes(self, data):
        print("Received binary data")
        """Handle incoming binary data (file chunks) from the device."""
        file_name = self.file_name

        # Get the current directory of the script
        current_dir = os.path.dirname(os.path.abspath(__file__))

        # Construct the path to the adjacent 'files' directory
        file_dir = os.path.join(current_dir, 'files')

        # Ensure the 'files' directory exists, create it if it doesn't
        os.makedirs(file_dir, exist_ok=True)

        # Construct the full path for the file to be saved
        file_path = os.path.join(file_dir, file_name)

        # Open the file in binary mode and append the incoming data
        with open(file_path, 'ab') as f:
            f.write(data)
            print(f"Received {len(data)} bytes and written to {file_path}")

        # After writing the last chunk
        await self.send(text_data=json.dumps({
            'message': f"File {self.file_name} transfer completed.",
            'status': 'download_complete',
            'file_name': self.file_name
        }))

    async def finalize_file_transfer(self, file_name):
        """This function is called when file transfer is complete."""
        # Notify the original client (or process as needed)
        await self.send(text_data=json.dumps({
            'message': f"File {file_name} transfer completed."
        }))



