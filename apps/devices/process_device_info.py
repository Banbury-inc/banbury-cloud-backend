from .update_device import update_device

def process_device_info(request, sending_device_name, requesting_device_name, device_info):
    """
    Processes incoming device information by calling the update_device function.

    Acts as a wrapper or entry point for updating device details based on
    information received.

    Args:
        username (str): The username of the device owner.
        sending_device_name (str): The name of the device sending the information.
        requesting_device_name (str): The name of the device that requested the info (unused by update_device).
        device_info (dict): A dictionary containing the device details to update.

    Returns:
        The result from the update_device function (typically "success" or an error string).
    """

    response = update_device(request.username_from_token, sending_device_name, requesting_device_name, device_info)

