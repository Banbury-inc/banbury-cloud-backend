from ..settings.get_settings import get_settings

class ScoringService():
    def __init__(self):
        pass
    def devices(self, performance_data, username):
        # Define the maximum and minimum for normalization from observed or expected ranges
        max_upload_speed = max(device['predicted_upload_speed'] for device in performance_data)
        min_upload_speed = min(device['predicted_upload_speed'] for device in performance_data)
        max_download_speed = max(device['predicted_download_speed'] for device in performance_data)
        min_download_speed = min(device['predicted_download_speed'] for device in performance_data)
        max_gpu_usage = max(device['predicted_gpu_usage'] for device in performance_data)
        min_gpu_usage = min(device['predicted_gpu_usage'] for device in performance_data)
        max_cpu_usage = max(device['predicted_cpu_usage'] for device in performance_data)
        min_cpu_usage = min(device['predicted_cpu_usage'] for device in performance_data)
        max_ram_usage = max(device['predicted_ram_usage'] for device in performance_data)
        min_ram_usage = min(device['predicted_ram_usage'] for device in performance_data)


        settings = get_settings(username)

        predicted_upload_speed_weighting = settings['settings'].get('predicted_upload_speed_weighting', 0.2)
        predicted_download_speed_weighting = settings['settings'].get('predicted_download_speed_weighting', 0.2) 
        predicted_gpu_usage_weighting = settings['settings'].get('predicted_gpu_usage_weighting', 0.2)
        predicted_cpu_usage_weighting = settings['settings'].get('predicted_cpu_usage_weighting', 0.2)
        predicted_ram_usage_weighting = settings['settings'].get('predicted_ram_usage_weighting', 0.2)

        # Calculate scores for each device
        for device in performance_data:
            normalized_upload_speed = (device['predicted_upload_speed'] - min_upload_speed) / (max_upload_speed - min_upload_speed) * 100
            normalized_download_speed = (device['predicted_download_speed'] - min_download_speed) / (max_download_speed - min_download_speed) * 100
            normalized_gpu_usage = (1 - (device['predicted_gpu_usage'] - min_gpu_usage) / (max_gpu_usage - min_gpu_usage)) * 100
            normalized_cpu_usage = (1 - (device['predicted_cpu_usage'] - min_cpu_usage) / (max_cpu_usage - min_cpu_usage)) * 100
            normalized_ram_usage = (1 - (device['predicted_ram_usage'] - min_ram_usage) / (max_ram_usage - min_ram_usage)) * 100

            # Compute weighted score
            device['score'] = (
                predicted_upload_speed_weighting * normalized_upload_speed +
                predicted_download_speed_weighting * normalized_download_speed +
                predicted_gpu_usage_weighting * normalized_gpu_usage +
                predicted_cpu_usage_weighting * normalized_cpu_usage +
                predicted_ram_usage_weighting * normalized_ram_usage
            )

        scored_devices = performance_data

        return scored_devices


def main():
    scoring_service = ScoringService()
    performance_data = [
        {
            "device_name": "device1",
            "predicted_upload_speed": 100,
            "predicted_download_speed": 200,
            "predicted_gpu_usage": 50,
            "predicted_cpu_usage": 50,
            "predicted_ram_usage": 50
        },
        {
            "device_name": "device2",
            "predicted_upload_speed": 200,
            "predicted_download_speed": 100,
            "predicted_gpu_usage": 100,
            "predicted_cpu_usage": 100,
            "predicted_ram_usage": 100
        }
    ]
    username = "mmills"
    print(scoring_service.devices(performance_data, username))

if __name__ == "__main__":
    main()
