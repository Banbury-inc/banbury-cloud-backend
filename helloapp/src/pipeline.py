# pipeline for prediction service

from .db.get_device_info import get_device_info
from .db.get_files_info import get_files_info
from .db.update_device_predictions import update_device_predictions
from .scoring_service import ScoringService
from .prediction_service import PredictionService
from .allocation_service import AllocationService

def pipeline(username): 
    try:
        device_info = get_device_info(username)
    except Exception as e:
        return {"error": f"Failed to get device info: {e}"}
    try:
        files_info = get_files_info(username)
    except Exception as e:
        return {"error": f"Failed to get files info: {e}"}
    try:
        prediction_service = PredictionService()
        device_predictions = prediction_service.performance_data(device_info, show_graph=False)
    except Exception as e:
        return {"error": f"Failed to predict devices: {e}"}
    try:
        results = []
        for device_prediction in device_predictions:
            result = update_device_predictions(
                username, 
                device_prediction['device_name'], 
                device_prediction
            )
            results.append(result)
    except Exception as e:
        return {"error": f"Failed to update device predictions: {e}"}
    #try:
    #    scored_devices = ScoringService().devices(predicted_devices)
    #    print(scored_devices)
    #except Exception as e:
    #    return {"error": f"Failed to score devices: {e}"}
    #try:
    #    allocated_devices = AllocationService().allocate(predicted_devices, files_info)
    #    print(allocated_devices)
    #except Exception as e:
    #    return {"error": f"Failed to allocate devices: {e}"}
    #return allocated_devices

if __name__ == "__main__":
    print(pipeline("mmills"))