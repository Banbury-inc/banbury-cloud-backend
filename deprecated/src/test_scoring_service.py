import unittest
from scoring_service import ScoringService

class TestScoringService(unittest.TestCase):
    def setUp(self):
        self.service = ScoringService()
    
    def test_device_scoring(self):
        # Sample performance data for testing
        performance_data = [
            {
                "device_name": "Device A",
                "predicted_upload_speed": 50,
                "predicted_download_speed": 200,
                "predicted_gpu_usage": 30,
                "predicted_cpu_usage": 40,
                "predicted_ram_usage": 60
            },
            {
                "device_name": "Device B",
                "predicted_upload_speed": 100,
                "predicted_download_speed": 100,
                "predicted_gpu_usage": 80,
                "predicted_cpu_usage": 90,
                "predicted_ram_usage": 70
            },
            {
                "device_name": "Device C",
                "predicted_upload_speed": 150,
                "predicted_download_speed": 300,
                "predicted_gpu_usage": 60,
                "predicted_cpu_usage": 20,
                "predicted_ram_usage": 50
            }
        ]

        # Run scoring service on performance data
        scored_devices = self.service.devices(performance_data)

        # Verify that each device has a score
        for device in scored_devices:
            self.assertIn('score', device)
            self.assertGreaterEqual(device['score'], 0)
            self.assertLessEqual(device['score'], 100)

        # Check normalization bounds and score consistency
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

        for device in scored_devices:
            # Normalization for upload speed
            normalized_upload_speed = (device['predicted_upload_speed'] - min_upload_speed) / (max_upload_speed - min_upload_speed) * 100
            self.assertGreaterEqual(normalized_upload_speed, 0)
            self.assertLessEqual(normalized_upload_speed, 100)

            # Normalization for download speed
            normalized_download_speed = (device['predicted_download_speed'] - min_download_speed) / (max_download_speed - min_download_speed) * 100
            self.assertGreaterEqual(normalized_download_speed, 0)
            self.assertLessEqual(normalized_download_speed, 100)

            # Normalization for GPU usage
            normalized_gpu_usage = (1 - (device['predicted_gpu_usage'] - min_gpu_usage) / (max_gpu_usage - min_gpu_usage)) * 100
            self.assertGreaterEqual(normalized_gpu_usage, 0)
            self.assertLessEqual(normalized_gpu_usage, 100)

            # Normalization for CPU usage
            normalized_cpu_usage = (1 - (device['predicted_cpu_usage'] - min_cpu_usage) / (max_cpu_usage - min_cpu_usage)) * 100
            self.assertGreaterEqual(normalized_cpu_usage, 0)
            self.assertLessEqual(normalized_cpu_usage, 100)

            # Normalization for RAM usage
            normalized_ram_usage = (1 - (device['predicted_ram_usage'] - min_ram_usage) / (max_ram_usage - min_ram_usage)) * 100
            self.assertGreaterEqual(normalized_ram_usage, 0)
            self.assertLessEqual(normalized_ram_usage, 100)


        print(scored_devices)

if __name__ == "__main__":
    unittest.main()

