import json

async def handle_file_chunk(consumer, bytes_data):
    """
    Handle a binary file chunk received from the sender and forward it to the target transfer room.
    Assumes that the consumer has an attribute 'transfer_room' set when a file transfer starts.
    """
    print(f"===== BINARY CHUNK RECEIVED =====")
    print(f"Received binary chunk of length: {len(bytes_data)} bytes")
    
    # Try to get transfer room from consumer
    transfer_room = getattr(consumer, 'transfer_room', None)
    
    # If transfer_room is not set, try to get from consumer.scope
    if not transfer_room and hasattr(consumer, 'scope'):
        transfer_room = consumer.scope.get('transfer_room')
    
    # If still no transfer_room, check if we have active transfer rooms list
    if not transfer_room and hasattr(consumer, 'active_transfer_rooms'):
        if consumer.active_transfer_rooms:
            transfer_room = list(consumer.active_transfer_rooms)[0]
    
    if not transfer_room:
        print('No transfer room found on consumer; cannot forward file chunk.')
        print('Will broadcast to all connected clients instead.')
        
        # If we can't find a transfer room, try to send directly
        try:
            await consumer.send(bytes_data=bytes_data)
            print(f"Directly sent {len(bytes_data)} bytes to the connected client.")
            return
        except Exception as e:
            print(f"Error sending bytes directly: {str(e)}")
            return
    
    print(f"Forwarding {len(bytes_data)} bytes to transfer room: {transfer_room}")
    
    # Forward the binary chunk to the designated transfer room using the channel layer
    try:
        await consumer.channel_layer.group_send(
            transfer_room,
            {
                'type': 'forward_file_chunk',
                'bytes_data': bytes_data
            }
        )
        print(f"Successfully forwarded binary chunk to room {transfer_room}")
    except Exception as e:
        print(f"Error forwarding binary chunk: {str(e)}")
        # Try direct send as fallback
        try:
            await consumer.send(bytes_data=bytes_data)
            print(f"Fallback: Directly sent {len(bytes_data)} bytes to the connected client.")
        except Exception as send_error:
            print(f"Error in fallback direct send: {str(send_error)}")


async def forward_file_chunk(consumer, event):
    """
    Receive a forwarded binary file chunk event and send it to the client using bytes_data.
    """
    bytes_data = event.get('bytes_data')
    if bytes_data:
        print(f"Forwarding binary chunk of {len(bytes_data)} bytes to client")
        await consumer.send(bytes_data=bytes_data)
        print(f"Successfully forwarded {len(bytes_data)} bytes to client")
    else:
        print("Warning: Received forward_file_chunk event with no bytes_data") 