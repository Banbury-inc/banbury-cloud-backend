# Add this import if broadcast_new_file exists elsewhere
from websocket.utils import broadcast_new_file as ws_broadcast_new_file

def broadcast_new_file(file_metadata):
    """
    Broadcast new file metadata through websocket.
    
    Args:
        file_metadata (dict): The file metadata to broadcast
        
    Returns:
        The result from the websocket broadcast function
    """
    # Call the actual broadcast function from the websocket module
    return ws_broadcast_new_file(file_metadata) 