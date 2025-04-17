# pipeline for prediction service

from apps.devices.get_device_info import get_device_info
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
from datetime import datetime
import asyncio

async def pipeline(username):
    """Executes the end-to-end prediction and allocation pipeline for a user.

    Steps:
    1. Fetches current device information, existing predictions, and file sync info.
    2. Checks if device predictions are older than 30 minutes.
    3. If outdated:
        a. Runs the PredictionService to generate new performance predictions.
        b. Updates device predictions in the database.
        c. Runs the ScoringService to calculate device scores based on predictions.
        d. Updates device scores in the database.
        e. Fetches the updated predictions (including scores).
        f. Runs the AllocationService to allocate files to devices based on scores.
        g. Generates file-to-device mappings from the allocation.
        h. Updates the 'proposed_device_ids' for each file in the 'file_sync' collection.
        i. For each allocated device, gets its download queue (needed vs. available files).
        j. Updates the download queue status (files_needed, files_available_for_download)
           in the device predictions collection.
    4. If predictions are up-to-date:
        a. Runs AllocationService with existing predictions.
        b. Generates file-to-device mappings.
        c. Gets the download queue for each device.

    Args:
        username (str): The username for whom to run the pipeline.

    Returns:
        dict: A dictionary containing:
              - "success": A success message string.
              - "results": A list of results from update operations (may be empty).
              - "allocated_devices": The output from the AllocationService.
              - "file_device_mappings": The generated file-to-device mappings.
              - "download_queue": The download queue for the last processed device.
              Or an error dictionary if any step fails.
    """
    try:
        device_info = get_device_info(username)
    except Exception as e:
        return {"error": f"Failed to get device info: {e}"}
    try:
        predictions_result = get_device_predictions(username)
    except Exception as e:
        return {"error": f"Failed to get device predictions: {e}"}
    try:
        file_sync_info = get_file_sync(username)
    except Exception as e:
        return {"error": f"Failed to get files info: {e}"}

    
    results = []
    for device_prediction in predictions_result['device_predictions']:
        # get the current time
        current_time = datetime.now()
        # if the prediction is more than 30 minutes old, update it
        prediction_time = device_prediction['timestamp']
        time_diff = (current_time - prediction_time).total_seconds()
        if time_diff > 1800:
            print("device predictions haven't been updated in 30 minutes, updating")
            try:
                prediction_service = PredictionService()
                device_predictions = await prediction_service.performance_data(
                    device_info, show_graph=False)
            except Exception as e:
                return {"error": f"Failed to predict devices: {e}"}
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

                # Generate file-to-device mappings
                file_device_mappings = AllocationService(
                ).generate_file_device_mappings(allocated_devices)

                # Update each file's proposed device IDs
                for mapping in file_device_mappings:
                    try:
                        # Verify mapping has expected format before updating
                        if not isinstance(mapping.get('proposed_device_ids', []), list):
                            print(f"Invalid proposed_device_ids format for file {mapping.get('file_id')}")
                            continue
                            
                        result = update_file_sync_proposed_device_ids(
                            username=username,
                            file_id=mapping['file_id'],
                            proposed_device_ids=mapping['proposed_device_ids']  # This should be a simple list of device IDs
                        )
                        if 'error' in result:
                            print("Error updating file sync proposed device ids: ", result)
                    except Exception as e:
                        print(f"Failed to update file sync proposed device ids: {e}")

            except Exception as e:
                return {"error": f"Failed in allocation pipeline: {e}"}


            # for each device, get the download queue
            for device in allocated_devices:
                download_queue = get_download_queue(username, device['device_id'])

                
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

            print(results)



            return {"success": "Pipeline executed successfully",
                    "results": results,
                    "allocated_devices": allocated_devices,
                    "file_device_mappings": file_device_mappings,
                    "download_queue": download_queue
                    }


        else:
            print("device predictions are up to date")

            allocated_devices = AllocationService().devices(
                predictions_result, file_sync_info)

            # Generate file-to-device mappings
            file_device_mappings = AllocationService(
            ).generate_file_device_mappings(allocated_devices)

            for device in allocated_devices:
                download_queue = get_download_queue(username, device_prediction['device_id'])


            return {"success": "Pipeline executed successfully",
                    "results": results,
                    "allocated_devices": allocated_devices,
                    "file_device_mappings": file_device_mappings,
                    "download_queue": download_queue
                    }


def main():
    result = asyncio.run(pipeline("mmills"))
    print(result)


if __name__ == "__main__":
    main()
