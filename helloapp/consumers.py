
import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from .src.search_for_file import search_for_file

connected_devices = {}

class Live_Data(AsyncWebsocketConsumer):
    async def connect(self):


        await self.accept()

    async def disconnect(self, close_code):
        # Handle WebSocket disconnection
        pass

    async def receive(self, text_data):
        # Receive data from WebSocket and process it
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        username = text_data_json['username']
        device_name = text_data_json['device_name']

        print(f"Message: {message}", f"Username: {username}", f"Device Name: {device_name}")

        if device_name not in connected_devices:
            connected_devices[device_name] = self
            print(f"Device {device_name} connected.")

        if message == "Initiate live data connection":
            # Send a confirmation back to the client
            await self.send(text_data=json.dumps({
                'message': f"Live data connection initiated for {device_name}"
            }))



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
