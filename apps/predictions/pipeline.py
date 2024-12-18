# pipeline for prediction service

from apps.devices.get_device_info import get_device_info
from apps.files.get_files_info import get_files_info
from apps.predictions.get_file_sync import get_file_sync
from apps.predictions.get_device_predictions import get_device_predictions
from apps.predictions.update_device_predictions import update_device_predictions
from apps.predictions.update_device_score import update_device_score
from apps.predictions.update_file_sync_proposed_device_ids import update_file_sync_proposed_device_ids
from apps.predictions.get_download_queue import get_download_queue
from apps.predictions.scoring_service import ScoringService
from apps.predictions.prediction_service import PredictionService
from apps.predictions.allocation_service import AllocationService
from apps.predictions.update_download_queue import update_download_queue


def pipeline(username):
    try:
        device_info = get_device_info(username)
    except Exception as e:
        return {"error": f"Failed to get device info: {e}"}
    try:
        file_sync_info = get_file_sync(username)
    except Exception as e:
        return {"error": f"Failed to get files info: {e}"}
    try:
        prediction_service = PredictionService()
        device_predictions = prediction_service.performance_data(
            device_info, show_graph=False)
    except Exception as e:
        return {"error": f"Failed to predict devices: {e}"}
    results = []
    for device_prediction in device_predictions:
        try:
            result = update_device_predictions(
                username,
                device_prediction['device_name'],
                device_prediction
            )
            results.append(result)
        except Exception as e:
            return {"error": f"Failed to update device predictions: {e}"}
    try:
        scored_devices = ScoringService().devices(device_predictions)
        print(scored_devices)
    except Exception as e:
        return {"error": f"Failed to score devices: {e}"}

    try:
        results = []
        for scored_device in scored_devices:
            result = update_device_score(
                username,
                scored_device['device_name'],
                scored_device['score']
            )
            results.append(result)
    except Exception as e:
        return {"error": f"Failed to update device scores: {e}"}

    fetched_device_predictions = get_device_predictions(username)

    try:
        allocated_devices = AllocationService().devices(
            fetched_device_predictions, file_sync_info)
        print("Allocated devices:", allocated_devices)

        # Generate file-to-device mappings
        file_device_mappings = AllocationService(
        ).generate_file_device_mappings(allocated_devices)
        print("File device mappings:", file_device_mappings)

        # Update each file's proposed device IDs
        for mapping in file_device_mappings:
            try:
                result = update_file_sync_proposed_device_ids(
                    username=username,
                    file_id=mapping['file_id'],
                    proposed_device_ids=mapping['proposed_device_ids']
                )
                if 'error' in result:
                    print("Error updating file")
            except Exception as e:
                print(f"Failed to update file {mapping['file_id']}: {e}")

    except Exception as e:
        return {"error": f"Failed in allocation pipeline: {e}"}

    # for each device, get the download queue
    for device in allocated_devices:
        download_queue = get_download_queue(username, device['device_id'])

        print(f"Download queue for {device['device_name']}: {download_queue}")
        
        # Check if download_queue is a dictionary
        if isinstance(download_queue, dict):
            try:
                result = update_download_queue(
                    username,
                    device.get('device_name', ''),
                    download_queue.get('files_needed', []),
                    download_queue.get('files_available_for_download', [])
                )
                results.append(result)
            except Exception as e:
                print(f"Failed to update download queue: {result}")
        else:
            print(f"Error getting download queue: {download_queue}")



    return {"success": "Pipeline executed successfully",
            "results": results,
            "allocated_devices": allocated_devices,
            "file_device_mappings": file_device_mappings,
            "download_queue": download_queue
            }


if __name__ == "__main__":
    print(pipeline("mmills"))
