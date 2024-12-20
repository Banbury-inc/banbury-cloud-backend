import json

async def broadcast_new_file(file_name):
    """
    Broadcast a new file notification to all connected websockets.
    
    Args:
        file_name (str): The name of the new file
    """



async def announce_connection(websocket_connections, device_name, file_name, requesting_device_name):
    print(f"Announcing connection for {device_name}")
    for connection_id, connection in websocket_connections.items():
        await connection.send(text_data=json.dumps({
            'message': f"Requesting file {file_name}",
            'request_type': 'file_request',
            'file_name': file_name,
            'requesting_device_name': requesting_device_name  # Use self.device_name for the requesting device
        }))