
import json
import os
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from .src.search_for_file import search_for_file
from .src.declare_device_offline import declare_device_offline
from .src.declare_device_online import declare_device_online

connected_devices = {}


class Live_Data(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        # Set a flag to track if the connection logic has been triggered
        self.connect_triggered = False

    async def disconnect(self, close_code):
        device_name = self.scope.get('requesting_device_name')
        username = self.scope.get('username')

        if device_name:
            await self.trigger_post_disconnect(username, device_name)

    async def trigger_connect(self, username, device_name):
        """Custom function to handle what happens after disconnect."""
        print(f"Performing actions after {device_name} disconnects.")
        declare_device_online(username, device_name)
        print(f"Device {device_name} is now online.")



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
            await self.receive_bytes(bytes_data)
        elif text_data is not None and isinstance(text_data, str):
            # Handle the text data (JSON messages)
            await self.receive_text(text_data)

    async def receive_text(self, text_data):
        """Handle incoming text data."""
        try:
            text_data_json = json.loads(text_data)

            # Check if 'device_name' exists in the incoming message
            if 'requesting_device_name' not in text_data_json:
                print("Error: 'requesting_device_name' not found in the message")
                print(text_data_json)
                await self.send(text_data=json.dumps({'error': "'requesting_device_name' not found"}))
                return

            # Check if 'device_name' exists in the incoming message
            if 'requesting_device_name' in text_data_json:
                print("Device name found in the message, adding to scope")
                self.scope['requesting_device_name'] = text_data_json['requesting_device_name']

            # Check if 'device_name' exists in the incoming message
            if 'username' in text_data_json:
                print("Username found in the message, adding to scope")
                self.scope['username'] = text_data_json['username']

            # Once both username and device_name are available, trigger the connect action
            username = self.scope.get('username')
            device_name = self.scope.get('requesting_device_name')

            if username and device_name and not self.connect_triggered:
                # Trigger the connect logic only once
                await self.trigger_connect(username, device_name)
                # Mark connect as triggered
                self.connect_triggered = True


            if 'file_name' in text_data_json:
                # Set the file name in the WebSocket's scope
                self.scope['file_name'] = text_data_json['file_name']
                print(f"File name set in WebSocket scope: {self.scope['file_name']}")

            message = text_data_json['message']
            sending_device_name = text_data_json['sending_device_name'] if 'sending_device_name' in text_data_json else None
            requesting_device_name = text_data_json['requesting_device_name'] if 'requesting_device_name' in text_data_json else None
            username = text_data_json['username']
            file_name = text_data_json['file_name'] if 'file_name' in text_data_json else None
            if file_name:
                self.scope['file_name'] = file_name
                print(f"File name set in WebSocket scope: {self.scope['file_name']}")

            print(f"Message: {message}, Device Name: {requesting_device_name}")

            # Register the device WebSocket
            if requesting_device_name not in connected_devices:
                connected_devices[requesting_device_name] = self
                print(f"Device {requesting_device_name} connected.")

            if message == "Initiate live data connection":
                await self.send(text_data=json.dumps({
                    'message': f"Live data connection initiated for {requesting_device_name}"
                }))
            if message == "Download Request":
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
                    sending_device_name = file_data['device_name']  # The device that contains the file

                    # Send 'Found file, requesting...' message
                    response = f"Found file on {sending_device_name}, requesting..."
                    await self.send(text_data=json.dumps({
                        'message': response,
                        'request_type': 'update'
                    }))

                    # Look up the WebSocket connection for the device that contains the file
                    if sending_device_name in connected_devices:
                        device_ws = connected_devices[sending_device_name]
                        print(f"Sending request to device {sending_device_name} via Live_Data WebSocket...")

                        # Send a request to the device WebSocket to send the file
                        await device_ws.send(text_data=json.dumps({
                            'message': f"Requesting file {file_name} from {sending_device_name}",
                            'request_type': 'file_request',
                            'username': username,
                            'requesting_device_name': requesting_device_name,
                            'sending_device_name': sending_device_name,
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
                        response = f"Device {sending_device_name} is not connected."
                        await self.send(text_data=json.dumps({
                            'message': response
                        }))
            else:
                # If file not found
                response = "File not found."
                await self.send(text_data=json.dumps({
                    'message': response
                }))

            if message == "File sent successfully":
                # Send 'Searching for file...' message
                print("Entire file received, sending to requesting client...")

                # Look up the WebSocket connection for the device that contains the file
                if requesting_device_name in connected_devices:
                    device_ws = connected_devices[requesting_device_name]
                    print(f"Sending request to device {requesting_device_name} via Live_Data WebSocket...")

                    response = "Sending requested file!"
                    await device_ws.send(text_data=json.dumps({
                        'message': response,
                        'username': username,
                        'file_name': file_name,
                        'requesting_device_name': requesting_device_name,
                        'sending_device_name': sending_device_name
                    }))
     
                    file_name = self.scope.get("file_name")  # Store the file name in the WebSocket's scope    

                    """Send the file in chunks over WebSocket."""
                    try:

                        current_dir = os.path.dirname(os.path.abspath(__file__))
                        file_dir = os.path.join(current_dir, 'files')

                        # set the file path
                        file_path = os.path.join(file_dir, file_name)

                        # Open the file in binary mode
                        with open(file_path, 'rb') as file:
                            while True:
                                # Read the file in chunks (e.g., 1024 bytes per chunk)
                                chunk = file.read(1024)
                                if not chunk:
                                    break

                                # Send the chunk as binary data via WebSocket
                                await device_ws.send(bytes_data=chunk)

                        # Once all chunks are sent, notify the client that the file transfer is complete
                        await device_ws.send(text_data=json.dumps({
                            'message': "File transfer complete",
                            'file_name': file_name,
                            'requesting_device_name': requesting_device_name,
                            'sending_device_name': sending_device_name,
                        }))
                    except FileNotFoundError:
                                    print(f"File {file_name} not found.")
                                    await device_ws.send(text_data=json.dumps({
                                        'message': "File not found",
                                        'file_name': file_name
                                    }))
            if message == "Download complete":
                print("Download complete")





        except json.JSONDecodeError:
            print("Error parsing JSON data.")
            await self.send(text_data=json.dumps({'error': "Invalid JSON format"}))

    async def receive_bytes(self, bytes_data):
        file_name = self.scope.get("file_name")  # Store the file name in the WebSocket's scope
        print(f"File name in WebSocket scope: {file_name}")
        # Save the file chunks to the 'files' directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_dir = os.path.join(current_dir, 'files')
        os.makedirs(file_dir, exist_ok=True)
        file_path = os.path.join(file_dir, file_name)

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


class Download_File_Request(AsyncWebsocketConsumer):
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

            # Look up the WebSocket connection for the device that contains the file
            if device_name in connected_devices:
                device_ws = connected_devices[device_name]
                print(f"Sending request to device {device_name} via Live_Data WebSocket...")

                # Send a request to the device WebSocket to send the file
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
            response = "File not found."
            await self.send(text_data=json.dumps({
                'message': response
            }))

    async def receive_bytes(self, data):
        """Handle incoming binary data (file chunks) from the device."""
        file_name = self.scope.get("file_name")  # Store the file name in the WebSocket's scope
        if not file_name:
            print("File name not found in WebSocket scope.")
            return

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

        # You can add additional logic to notify when the transfer is complete if necessary

    async def finalize_file_transfer(self, file_name):
        """This function is called when file transfer is complete."""
        # Notify the original client (or process as needed)
        await self.send(text_data=json.dumps({
            'message': f"File {file_name} transfer completed."
        }))
        print(f"File {file_name} has been fully transferred.")


