import json
import os
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from .src.search_for_file import search_for_file
from .src.declare_device_offline import declare_device_offline
from .src.declare_device_online import declare_device_online
from .src.get_online_devices import get_online_devices
from .src.process_device_info import process_device_info

connected_devices = {}


class Live_Data(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)
        self.file_name = None
        self.device_info_task = None

    async def connect(self):
        await self.accept()
        # Set a flag to track if the connection logic has been triggered
        self.connect_triggered = False
        device_name = self.scope.get('requesting_device_name')
        username = self.scope.get('username')
        connected_devices[device_name] = self
        print(f"Device {device_name} is now connected.")
        print(f"Connected Devices: {connected_devices}")


    async def disconnect(self, close_code):
        device_name = self.scope.get('requesting_device_name')
        username = self.scope.get('username')
        connected_devices.pop(device_name)
        print(f"Device {device_name} is now disconnected.")
        print(f"Connected Devices: {connected_devices}")

        if device_name:
            await self.trigger_post_disconnect(username, device_name)

        # Cancel the device info task if it's running
        if self.device_info_task:
            self.device_info_task.cancel()

    async def start_device_info_loop(self, username, device_name):
        """Start a loop to periodically update device information."""
        while True:
            await self.request_device_info(username, device_name)
            await asyncio.sleep(600)  # Sleep for 10 minutes (600 seconds)

    async def request_device_info(self, username, device_name):
        """Request device information from the device."""
        await self.send(text_data=json.dumps({
            'message': "Requesting device information",
            'request_type': 'device_info'
        }))

    async def trigger_connect(self, username, device_name):
        """Custom function to handle what happens after connect."""
        print(f"Performing actions after {device_name} connects.")
        declare_device_online(username, device_name)
        print(f"Device {device_name} is now online.")

        # Start device info loop
        print(f"Starting device info loop for {device_name}")
        self.device_info_task = asyncio.create_task(self.start_device_info_loop(username, device_name))


    async def trigger_post_disconnect(self, username, device_name):
        """Custom function to handle what happens after disconnect."""
        print(f"Performing actions after {device_name} disconnects.")
        declare_device_offline(username, device_name)
        print(f"Device {device_name} is now offline.")

    async def receive(self, text_data=None, bytes_data=None):
        """Handle both text and binary data based on the type of the input."""
        
        # Check if the data is bytes (binary data)
        if bytes_data is not None and isinstance(bytes_data, (bytes, bytearray)):
            # Handle the binary data (file chunks)
            print("Received binary data")
            await self.receive_bytes(bytes_data)
        elif text_data is not None and isinstance(text_data, str):
            # Handle the text data (JSON messages)
            try:
                text_data_json = json.loads(text_data)
                if 'file_name' in text_data_json:
                    self.file_name = text_data_json['file_name']
                    print(f"File name set in WebSocket scope: {self.file_name}")
                await self.receive_text(text_data)
            except json.JSONDecodeError:
                print("Error parsing JSON data.")
                await self.send(text_data=json.dumps({'error': "Invalid JSON format"}))

    async def receive_text(self, text_data):
        """Handle incoming text data."""
        try:
            text_data_json = json.loads(text_data)
            print(text_data_json)

            # Validate required fields
            if 'requesting_device_name' not in text_data_json:
                await self.send(text_data=json.dumps({
                    'message': 'Permission denied',
                    'error': "'requesting_device_name' not found"
                }))
                return

            # Add username and device name to scope
            if 'username' in text_data_json:
                self.scope['username'] = text_data_json['username']
            
            username = self.scope.get('username')
            device_name = self.scope.get('requesting_device_name')

            if not username or not device_name:
                await self.send(text_data=json.dumps({
                    'message': 'Permission denied',
                    'error': "Missing username or device name"
                }))
                return

            # Handle download request
            if text_data_json.get('message') == "Download Request":
                if 'file_name' not in text_data_json:
                    await self.send(text_data=json.dumps({
                        'message': 'Transfer failed',
                        'error': "File name not provided"
                    }))
                    return

                file_info = search_for_file(username, self.file_name)
                if not file_info or 'file_data' not in file_info:
                    await self.send(text_data=json.dumps({
                        'message': 'File not found',
                        'file_name': self.file_name
                    }))
                    return

                file_data = file_info['file_data']
                sending_device_name = file_data['device_name']

                if sending_device_name not in connected_devices:
                    await self.send(text_data=json.dumps({
                        'message': 'Device offline',
                        'sending_device_name': sending_device_name
                    }))
                    return

                # Rest of the download request handling...

            # Handle file transfer completion
            elif text_data_json.get('message') == "File sent successfully":
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
        print("Received binary data in receive bytes function")
        # Save the file chunks to the 'files' directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_dir = os.path.join(current_dir, 'files')
        os.makedirs(file_dir, exist_ok=True)
        file_path = os.path.join(file_dir, "temporary_file_name")

        # Write the binary data to the file
        with open(file_path, 'ab') as f:
            f.write(bytes_data)
            print(f"Received {len(bytes_data)} bytes and written to {file_path}")

    async def finalize_file_transfer(self, file_name):
        """This function is called when file transfer is complete."""
        await self.send(text_data=json.dumps({
            'message': f"File {file_name} transfer completed."
        }))
        print(f"File {file_name} has been fully transferred.")

async def broadcast_new_file(new_file):
    for device_name, device_ws in connected_devices.items():
        await device_ws.send(text_data=json.dumps({
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
            print(f"File name set in WebSocket scope: {self.scope['file_name']}")

        print(message)
        print(username)
        print(file_name)

        # Send 'Searching for file...' message
        response = "Searching for file..."
        await self.send(text_data=json.dumps({
            'message': response
        }))

        # Search for the file and the device that has it
        file_info = search_for_file(username, file_name)

        if file_info and 'file_data' in file_info:
            file_data = file_info['file_data']  # Extract the file_data dict
            print(file_data)

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
                    print(f"Sending request to device {device_name} via Live_Data WebSocket... in connected devices if statement")
                    print(f"Device WS: {device_ws}")
                    file_name = self.scope.get("file_name")
                    print(file_name)

                    # Send a request to each device WebSocket to check for the file
                    await device_ws.send(text_data=json.dumps({
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
                print(f"Sending request to device {device_name} via Live_Data WebSocket... in device name if statement")
                print(f"Device WS: {device_ws}")
                print(file_name)
                file_name = self.scope.get("file_name")
                print(file_name)

                # Send a request to the device WebSocket to send the file
                await device_ws.send(text_data=json.dumps({
                    'message': f"Requesting file {file_name} from {device_name}",
                    'request_type': 'file_request',
                    'file_name': file_name
                }))

                await device_ws.send(text_data=json.dumps({
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
        """Handle incoming binary data (file chunks) from the device."""
        file_name = self.file_name
        print(file_name)

        print("received bytes in the other receive bytes function")

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
        print(f"File {file_name} has been fully transferred.")




