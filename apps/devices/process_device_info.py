from .update_device import update_device

def process_device_info(username, sending_device_name, requesting_device_name, device_info):
    print(f"Device info received from {sending_device_name} for {username}")
    print(device_info)

    response = update_device(username, sending_device_name, requesting_device_name, device_info)
    print(response)

