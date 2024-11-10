# pipeline for prediction service

from .db.get_device_info import get_device_info

def pipeline(username): 
    try:
        device_info = get_device_info(username)
        return device_info
    except Exception as e:
        return {"error": f"Failed to run pipeline: {e}"}
