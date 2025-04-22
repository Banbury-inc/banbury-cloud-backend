import json
from datetime import datetime

async def handle_cancel_download_request(consumer, data):
    """Handles a request to cancel an ongoing file download."""
    filename = data.get("filename")
    requesting_device_id = data.get("requesting_device_id")
    # These need to be sent by the client initiating the cancel request
    sending_device_id = data.get("sending_device_id")
    transfer_room = data.get("transfer_room")

    if not all([filename, requesting_device_id, sending_device_id, transfer_room]):
        print(f"Error: Missing data for cancel request. Received: {data}")
        await consumer.send(text_data=json.dumps({
            "type": "error",
            "message": "Missing required information for cancelling download (filename, requesting_device_id, sending_device_id, transfer_room)"
        }))
        return

    print(f"Received cancel request for file '{filename}' in room '{transfer_room}'")
    print(f"Requesting device: {requesting_device_id}, Sending device: {sending_device_id}")

    try:
        # Notify the sending device to stop sending
        sending_device_group = f"device_{sending_device_id}"
        await consumer.channel_layer.group_send(
            sending_device_group,
            {
                # This type needs a corresponding handler method in the Consumer class
                "type": "cancel_transfer_event",
                "transfer_room": transfer_room,
                "filename": filename,
                "requesting_device_id": requesting_device_id,
                "timestamp": datetime.now().isoformat()
            }
        )
        print(f"Sent cancel_transfer_event to group {sending_device_group}")

        # Remove the requesting device from the transfer room group
        # This stops the requester from receiving further file chunks for this transfer
        await consumer.channel_layer.group_discard(
            transfer_room,
            consumer.channel_name
        )
        print(f"Removed requesting consumer {consumer.channel_name} from group {transfer_room}")

        # Clean up consumer's internal state related to this transfer room
        if hasattr(consumer, 'active_transfer_rooms'):
            consumer.active_transfer_rooms.discard(transfer_room)
        # Clear the main 'transfer_room' attribute only if it matches the cancelled room
        if getattr(consumer, 'transfer_room', None) == transfer_room:
            consumer.transfer_room = None
            print(f"Cleared consumer.transfer_room as it matched the cancelled room {transfer_room}")
        
        # Update scope state as well for redundancy
        if consumer.scope.get('transfer_rooms'):
            consumer.scope['transfer_rooms'].discard(transfer_room)
        if consumer.scope.get('transfer_room') == transfer_room:
            consumer.scope['transfer_room'] = None


        # Send confirmation back to the requesting device
        await consumer.send(text_data=json.dumps({
            "type": "download_cancelled",
            "filename": filename,
            "transfer_room": transfer_room,
            "success": True,
            "timestamp": datetime.now().isoformat()
        }))
        print(f"Sent download_cancelled confirmation to requesting device")

    except Exception as e:
        print(f"Error handling cancel download request: {str(e)}")
        await consumer.send(text_data=json.dumps({
            "type": "error",
            "message": f"Failed to process cancel download request: {str(e)}"
        }))

# This method needs to be added to the Consumer class to handle the group_send message type
# It extracts the event data and sends it directly to the consumer instance via WebSocket.
async def cancel_transfer_event(consumer, event):
    """
    Handler for the 'cancel_transfer_event' type sent via channel layers.
    This forwards the cancellation instruction to the specific consumer (sending device).
    """
    print(f"Forwarding cancel_transfer_event to consumer: {event}")
    await consumer.send(text_data=json.dumps({
        # The actual message type the frontend client (sender) should listen for
        "type": "cancel_transfer",
        "transfer_room": event.get("transfer_room"),
        "filename": event.get("filename"),
        "requesting_device_id": event.get("requesting_device_id"),
        "timestamp": event.get("timestamp")
    }))