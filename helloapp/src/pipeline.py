# pipeline for prediction service

from .db.get_device_info import get_device_info
from .db.get_files_info import get_files_info
from .scoring_service import ScoringService
from .prediction_service import PredictionService
from .allocation_service import AllocationService

def pipeline(username): 
    try:
        device_info = get_device_info(username)
        print(device_info)
    except Exception as e:
        return {"error": f"Failed to get device info: {e}"}
    try:
        files_info = get_files_info(username)
    except Exception as e:
        return {"error": f"Failed to get files info: {e}"}
    try:
        prediction_service = PredictionService()
        predicted_devices = prediction_service.performance_data(device_info, show_graph=False)
        print(predicted_devices)
    except Exception as e:
        return {"error": f"Failed to predict devices: {e}"}
    try:
        scored_devices = ScoringService().devices(device_info)
        print(scored_devices)
    except Exception as e:
        return {"error": f"Failed to score devices: {e}"}
    try:
        allocated_devices = AllocationService().allocate(predicted_devices, files_info)
        print(allocated_devices)
    except Exception as e:
        return {"error": f"Failed to allocate devices: {e}"}
    return allocated_devices

if __name__ == "__main__":
    print(pipeline("mmills"))