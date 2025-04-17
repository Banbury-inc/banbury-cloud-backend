import json

def device_group_name(device_id):
    """
    Generate a channel group name for the given device ID.
    Each device gets their own group, e.g. "device_123456".
    """
    return f"device_{device_id}"

async def handle_file_sent_successfully(consumer, data):
    """Handle file sent successfully"""
    print(f"Received file sent successfully: {data}")
    file_name = data.get("file_name")
    file_path = data.get("file_path")
    requesting_device_name = data.get("requesting_device_name")
    sending_device_name = data.get("sending_device_name")
    requesting_device_id = data.get("requesting_device_id")
    sending_device_id = data.get("sending_device_id")

    # Send completion message to requesting device
    await consumer.send(text_data=json.dumps({
        "type": "file_sent_successfully",
        "message": "File transfer complete",
        "file_name": file_name,
        "file_path": file_path,
        "requesting_device_id": requesting_device_id,
        "sending_device_id": sending_device_id,
        "sending_device_name": sending_device_name
    }))

    # Also notify the sending device
    await consumer.channel_layer.group_send(
        device_group_name(sending_device_id),
        {
            "type": "dm_event",
            "message": "File transfer complete",
            "requesting_device_id": requesting_device_id,
            "sending_device_id": sending_device_id,
            "file_name": file_name
        }
    )
