from datetime import datetime
from helloapp.src.prediction_service_multiple_times import PredictionServiceMultipleTimes

# Create test data
test_device = {
    'device_name': 'Test Device',
    'cpu_usage': [50, 55, 60, 58, 62],
    'ram_usage': [70, 72, 75, 73, 71],
    'gpu_usage': [30, 35, 32, 34, 36],
    'upload_speed': [100, 105, 98, 102, 103],
    'download_speed': [150, 155, 148, 152, 153],
    'current_time': [
        datetime.now().strftime("%Y-%m-%d %H:%M:%S") for _ in range(5)
    ]
}

# Create prediction service instance
prediction_service = PredictionServiceMultipleTimes()

# Get predictions
predictions = prediction_service.performance_data([test_device])

# Print predictions in a formatted table
for device_predictions in predictions:
    print(f"\nPredictions for device: {device_predictions['device_name']}\n")
    print("Timestamp | Upload Speed | Download Speed | GPU Usage | CPU Usage | RAM Usage")
    print("-" * 80)
    
    for prediction in device_predictions['predictions']:
        # Handle None values with a default string
        upload_speed = "N/A" if prediction['predicted_upload_speed'] is None else f"{prediction['predicted_upload_speed']}"
        download_speed = "N/A" if prediction['predicted_download_speed'] is None else f"{prediction['predicted_download_speed']}"
        gpu_usage = "N/A" if prediction['predicted_gpu_usage'] is None else f"{prediction['predicted_gpu_usage']}"
        cpu_usage = "N/A" if prediction['predicted_cpu_usage'] is None else f"{prediction['predicted_cpu_usage']}"
        ram_usage = "N/A" if prediction['predicted_ram_usage'] is None else f"{prediction['predicted_ram_usage']}"
        
        print(f"{prediction['timestamp']} | "
              f"{upload_speed} | "
              f"{download_speed} | "
              f"{gpu_usage} | "
              f"{cpu_usage} | "
              f"{ram_usage}")
