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
        self.file_path = None
        self.device_info_task = None
        self.device_predictions_task = None
        self.device_name = None
        self.requesting_device_name = None
        self.run_device_info_loop = None
        self.run_device_predictions_loop = None
        self.should_run = True
        # Use a combination of timestamp and id for truly unique connections
        self.connection_id = f"{time.time()}_{id(self)}"

    async def connect(self):
        await self.accept()
        device_name = self.scope.get('requesting_device_name')
        username = self.scope.get('username')

        print(f"New connection established:")
        print(f"- Connection ID: {self.connection_id}")
        print(f"- WebSocket: {self}")
        print(f"- Device name: {device_name}")
        print(f"- Username: {username}")
        
        # Check if this WebSocket object already exists in websocket_connections
        existing_ws = None
        for conn_id, device_info in connected_devices.items():
            if device_info['websocket'] == self:
                existing_ws = conn_id
                break
        
        if existing_ws:
            print(f"WebSocket object already exists with connection ID: {existing_ws}")
            # Create new WebSocket instance
            new_ws = AsyncWebsocketConsumer()
            new_ws.connection_id = self.connection_id
            new_ws.device_name = self.device_name
            self = new_ws
            print(f"Created new WebSocket instance with connection ID: {self.connection_id}")
        
        # Store connection with unique ID
        websocket_connections[self.connection_id] = self

        print(f"websocket_connections: {websocket_connections}")
        
        # Debug: Print all current connections
        print("Current WebSocket connections:")
        for conn_id, conn in websocket_connections.items():
            print(f"- {conn_id}: {conn.device_name if hasattr(conn, 'device_name') else 'unnamed'}")

            try:
                result = declare_device_online(username, device_name)
                print(f"[WebSocket] Device online declaration result: {result}")
                
                if isinstance(result, dict) and result.get('result') == 'success':
                    await self.trigger_connect(username, device_name)
                    if self.run_device_info_loop:
                        await self.start_device_info_loop(username, device_name, self.run_device_info_loop)
                    if self.run_device_predictions_loop:
                        await self.start_device_predictions_loop(username, device_name, self.run_device_predictions_loop)
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
            
            # Remove from both connection dictionaries
            if self.connection_id in connected_devices:
                connected_devices.pop(self.connection_id)
                print(f"Removed device connection for {device_name} with ID {self.connection_id}")
            
            if self.connection_id in websocket_connections:
                websocket_connections.pop(self.connection_id)
                print(f"Removed websocket connection with ID {self.connection_id}")

            print("Remaining connections:")
            print(f"- Connected devices: {list(connected_devices.keys())}")
            print(f"- WebSocket connections: {list(websocket_connections.keys())}")

            if device_name and username:
                await self.trigger_post_disconnect(username, device_name)
                
        except Exception as e:
            print(f"Error during disconnect: {e}")

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

        print(f"File name: {self.file_name}")
        
        # Check if the data is bytes (binary data)
        if bytes_data is not None and isinstance(bytes_data, (bytes, bytearray)):
            print("Received binary data")
            await self.receive_bytes(bytes_data)

        elif text_data is not None and isinstance(text_data, str):
            try:
                text_data_json = json.loads(text_data)
                print(f"text_data_json 490: {text_data_json}")
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
                    if device_name not in connected_devices:
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

                print(f"text_data_json: {text_data_json}")
                
                # Store file information in instance variables
                self.file_name = text_data_json['file_name']
                self.file_path = text_data_json.get('file_path', self.file_name)
                username = text_data_json['username']
                
                print(f"Setting up file transfer:")
                print(f"- File name: {self.file_name}")
                print(f"- File path: {self.file_path}")
                
                response = search_for_file(username, self.file_name)
                
                # Get device name that has the file
                sending_device_name = response.get('device_name')
                file_path = response.get('file_path')
                
                if file_path:
                    self.file_path = file_path

                if sending_device_name not in connected_devices:
                    await self.send(text_data=json.dumps({
                        'message': 'Device offline',
                        'sending_device_name': sending_device_name
                    }))
                    return
                
                # Use the device that has the file
                device_info = connected_devices[sending_device_name]
                sending_device_ws = device_info['websocket']
                
                # Send the request to the device that has the file
                await sending_device_ws.send(text_data=json.dumps({
                    'message': f"Requesting file {self.file_name}",
                    'request_type': 'file_request',
                    'file_name': self.file_name,
                    'file_path': self.file_path,
                    'requesting_device_name': self.device_name
                }))

            # Handle file transfer completion
            elif text_data_json.get('message') == "File sent successfully":
                file_name = text_data_json.get('file_name')
                file_path = text_data_json.get('file_path')
                print("File sent successfully 437")
                try:
                    print(f"connected_devices: {connected_devices} 439")
                    for device_info in connected_devices.values():
                        await device_info['websocket'].send(text_data=json.dumps({
                            'message': 'File transfer complete',
                            'file_name': file_name,
                            'file_path': file_path,
                            'requesting_device_name': text_data_json.get('requesting_device_name'),
                            'sending_device_name': text_data_json.get('sending_device_name')
                        }))
                except Exception as e:
                    await self.send(text_data=json.dumps({
                        'message': 'Transfer failed',
                        'error': str(e)
                    }))



            # Handle file transfer completion
            elif text_data_json.get('message') == "File transfer complete":
                print("File transfer complete")
                print(f"self.file_name 439: {self.file_name}")
                print(f"self.file_path 440: {self.file_path}")
                file_name = text_data_json.get('file_name')
                file_path = text_data_json.get('file_path')
                print(f"file_name 443: {file_name}")
                print(f"file_path 444: {file_path}")
                try:
                    # Send completion message to all connected devices
                    for device_info in connected_devices.values():
                        await device_info['websocket'].send(text_data=json.dumps({
                            'message': 'File transfer complete',
                            'file_name': file_name,
                            'file_path': file_path,
                            'requesting_device_name': text_data_json.get('requesting_device_name'),
                            'sending_device_name': text_data_json.get('sending_device_name')
                        }))
                except Exception as e:
                    # Send error to all connected devices
                    for device_info in connected_devices.values():
                        await device_info['websocket'].send(text_data=json.dumps({
                            'message': 'Transfer failed',
                            'error': str(e)
                        }))

            # Handle file transaction completion
            elif text_data_json.get('message') == "File transaction complete":
                print("File transaction complete")
                print(f"self.file_name 458: {self.file_name}")
                print(f"self.file_path 459: {self.file_path}")
                file_name = text_data_json.get('file_name')
                file_path = text_data_json.get('file_path')
                print(f"file_name 487: {file_name}")
                print(f"file_path 488: {file_path}")
                try:
                    # Send completion message to all connected devices
                    for device_info in connected_devices.values():
                        await device_info['websocket'].send(text_data=json.dumps({
                            'message': 'File transfer complete',
                            'file_name': file_name,
                            'file_path': file_path,
                            'requesting_device_name': text_data_json.get('requesting_device_name'),
                            'sending_device_name': text_data_json.get('sending_device_name')
                        }))
                except Exception as e:
                    # Send error to all connected devices
                    for device_info in connected_devices.values():
                        await device_info['websocket'].send(text_data=json.dumps({
                            'message': 'Transaction failed', 
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
        print("Received binary data")
        print(f"Processing binary data for file: {self.file_name}")

        for device_info in connected_devices.values():
            print(f"sending bytes to device_info: {device_info} 523")
            try:
                await device_info['websocket'].send(bytes_data=bytes_data)
                print(f"Forwarded {len(bytes_data)}")
            except Exception as e:
                print(f"Error forwarding data: {e}")


        # After writing the last chunk
        await self.send(text_data=json.dumps({
            'message': f"File {self.file_name} transfer completed.",
            'status': 'download_complete',
            'file_name': self.file_name,
            'file_path': self.file_path
        }))


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
        self.file_path = None
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
        file_path = text_data_json['file_path']
        if file_name:
            self.scope['file_name'] = file_name
            if file_path:
                self.scope['file_path'] = file_path
                self.file_path = file_path
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
            file_path = file_data['file_path']
            print(f"file_path 530: {file_path}")
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
                    file_path = self.scope.get("file_path")
                    print(f"file_path 546: {file_path}")
                    # Send a request to each device WebSocket to check for the file
                    await device_ws['websocket'].send(text_data=json.dumps({
                        'message': f"Requesting file {file_name} from {device_name}",
                        'request_type': 'file_request',
                        'file_name': file_name,
                        'file_path': file_path
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
                file_path = self.scope.get("file_path")
                print(f"file_path 566: {file_path}")
                # Send a request to the device WebSocket to send the file
                await device_ws['websocket'].send(text_data=json.dumps({
                    'message': f"Requesting file {file_name} from {device_name}",
                    'request_type': 'file_request',
                    'file_name': file_name,
                    'file_path': file_path
                }))

                await device_ws['websocket'].send(text_data=json.dumps({
                    'message': f"Requesting file {file_name} from {device_name}",
                    'request_type': 'file_request',
                    'file_name': file_name,
                    'file_path': file_path
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
            'file_name': file_name,
            'file_path': file_path
        }))

    async def receive_bytes(self, data):
        print("Received binary data")
        """Handle incoming binary data (file chunks) from the device."""
        file_name = self.file_name
        file_path = self.file_path

        # Get the current directory of the script
        current_dir = os.path.dirname(os.path.abspath(__file__))

        print(f"current_dir 613: {current_dir}")

        # Construct the path to the adjacent 'files' directory
        file_dir = os.path.join(current_dir, 'files')
        print(f"file_dir 617: {file_dir}")
        # Ensure the 'files' directory exists, create it if it doesn't
        os.makedirs(file_dir, exist_ok=True)

        # Construct the full path for the file to be saved
        file_path = os.path.join(file_dir, file_name)
        print(f"file_path 623: {file_path}")

        # Open the file in binary mode and append the incoming data
        with open(file_path, 'ab') as f:
            f.write(data)
            print(f"Received {len(data)} bytes and written to {file_path}")
            # send the byte data to the requesting device
            # Get the requesting device's websocket connection
            for device_name, device_ws in connected_devices.items():
                print(f"device_name: {device_name}")
                print(f"device_ws: {device_ws}")
                await device_ws['websocket'].send(bytes_data=data)

        # After writing the last chunk
        await self.send(text_data=json.dumps({
            'message': f"File {self.file_name} transfer completed.",
            'status': 'download_complete',
            'file_name': self.file_name,
            'file_path': self.file_path
        }))

    async def finalize_file_transfer(self, file_name):
        """This function is called when file transfer is complete."""
        # Notify the original client (or process as needed)
        await self.send(text_data=json.dumps({
            'message': f"File {file_name} transfer completed."
        }))



