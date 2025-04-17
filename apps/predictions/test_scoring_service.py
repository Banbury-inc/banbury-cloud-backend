import unittest
from scoring_service import ScoringService
import numpy as np

class TestScoringService(unittest.TestCase):
    def setUp(self):
        self.service = ScoringService()
    
    def test_device_scoring(self):
        # Sample performance data for testing
        performance_data = [
            {
                "device_name": "Device A",
                "predicted_upload_speed": 10.5,
                "predicted_download_speed": 50.2,
                "predicted_gpu_usage": 65.0,
                "predicted_cpu_usage": 70.0,
                "predicted_ram_usage": 80.0
            },
            {
                "device_name": "Device B",
                "predicted_upload_speed": 5.2,
                "predicted_download_speed": 30.1,
                "predicted_gpu_usage": 45.0,
                "predicted_cpu_usage": 90.0,
                "predicted_ram_usage": 60.0
            },
            {
                "device_name": "Device C",
                "predicted_upload_speed": 15.0,
                "predicted_download_speed": 60.0,
                "predicted_gpu_usage": 30.0,
                "predicted_cpu_usage": 50.0,
                "predicted_ram_usage": 70.0
            }
        ]
        
        # Test default weights
        scored_devices = self.service.device_scoring(performance_data)
        
        # Ensure all devices are scored
        self.assertEqual(len(scored_devices), 3)
        
        # Check that each device has a score field
        for device in scored_devices:
            self.assertIn('score', device)
            self.assertIsInstance(device['score'], float)
            
        # Verify scoring calculation based on default weights
        # Device C should have highest score (best upload/download, low GPU/CPU usage)
        self.assertTrue(scored_devices[2]['score'] > scored_devices[0]['score'])
        self.assertTrue(scored_devices[2]['score'] > scored_devices[1]['score'])
        
        # Device B should have lowest score (worst upload/download, high CPU)
        self.assertTrue(scored_devices[1]['score'] < scored_devices[0]['score'])
        self.assertTrue(scored_devices[1]['score'] < scored_devices[2]['score'])
    
    def test_device_scoring_custom_weights(self):
        # Sample performance data for testing
        performance_data = [
            {
                "device_name": "Device A",
                "predicted_upload_speed": 10.5,
                "predicted_download_speed": 50.2,
                "predicted_gpu_usage": 65.0,
                "predicted_cpu_usage": 70.0,
                "predicted_ram_usage": 80.0
            },
            {
                "device_name": "Device B",
                "predicted_upload_speed": 5.2,
                "predicted_download_speed": 30.1,
                "predicted_gpu_usage": 45.0,
                "predicted_cpu_usage": 90.0,
                "predicted_ram_usage": 60.0
            },
            {
                "device_name": "Device C",
                "predicted_upload_speed": 15.0,
                "predicted_download_speed": 60.0,
                "predicted_gpu_usage": 30.0,
                "predicted_cpu_usage": 50.0,
                "predicted_ram_usage": 70.0
            }
        ]
        
        # Custom weights prioritizing upload speed and low RAM usage
        custom_weights = {
            "upload_speed_weight": 0.5,
            "download_speed_weight": 0.1,
            "gpu_usage_weight": 0.0,
            "cpu_usage_weight": 0.1,
            "ram_usage_weight": 0.3
        }
        
        scored_devices = self.service.device_scoring(performance_data, custom_weights)
        
        # Ensure all devices are scored
        self.assertEqual(len(scored_devices), 3)
        
        # With these weights, Device C should still be top (highest upload), 
        # but Device A might score lower than B due to higher RAM usage
        self.assertTrue(scored_devices[2]['score'] > scored_devices[0]['score'])
        
    def test_device_scoring_with_insufficient_data(self):
        # Test with insufficient performance data
        incomplete_data = [
            {
                "device_name": "Device A",
                # Missing upload and download speeds
                "predicted_gpu_usage": 65.0,
                "predicted_cpu_usage": 70.0,
                "predicted_ram_usage": 80.0
            }
        ]
        
        # The service should gracefully handle missing metrics and still provide scores
        scored_devices = self.service.device_scoring(incomplete_data)
        
        # Ensure device is scored despite missing data
        self.assertEqual(len(scored_devices), 1)
        self.assertIn('score', scored_devices[0])
        
        # Score should be based only on available metrics
        # Since weights for missing metrics should default to 0, 
        # score will be based only on CPU/GPU/RAM usage
        expected_score = 100 - (0.1*65.0 + 0.2*70.0 + 0.1*80.0)
        self.assertAlmostEqual(scored_devices[0]['score'], expected_score, places=1)
    
    def test_device_scoring_with_custom_metrics(self):
        # Test with additional custom performance metrics
        custom_data = [
            {
                "device_name": "Device A",
                "predicted_upload_speed": 10.5,
                "predicted_download_speed": 50.2,
                "predicted_gpu_usage": 65.0,
                "predicted_cpu_usage": 70.0,
                "predicted_ram_usage": 80.0,
                "custom_metric": 95.0  # Custom metric that shouldn't affect scoring
            }
        ]
        
        scored_devices = self.service.device_scoring(custom_data)
        
        # Ensure device is scored and custom metric doesn't break scoring
        self.assertEqual(len(scored_devices), 1)
        self.assertIn('score', scored_devices[0])
        
        # Score should match expected calculation with default weights
        expected_score = (0.3*10.5 + 0.3*50.2) + (100 - (0.1*65.0 + 0.2*70.0 + 0.1*80.0))
        self.assertAlmostEqual(scored_devices[0]['score'], expected_score, places=1)
    
    def test_device_scoring_normalization(self):
        # Test normalization of scores across multiple devices with extreme values
        extreme_data = [
            {
                "device_name": "Super Fast Device",
                "predicted_upload_speed": 100.0,  # Very high upload speed
                "predicted_download_speed": 500.0,  # Very high download speed
                "predicted_gpu_usage": 5.0,       # Very low GPU usage
                "predicted_cpu_usage": 10.0,      # Very low CPU usage
                "predicted_ram_usage": 20.0       # Very low RAM usage
            },
            {
                "device_name": "Very Slow Device",
                "predicted_upload_speed": 0.5,    # Very low upload speed
                "predicted_download_speed": 1.0,  # Very low download speed
                "predicted_gpu_usage": 95.0,      # Very high GPU usage
                "predicted_cpu_usage": 90.0,      # Very high CPU usage
                "predicted_ram_usage": 95.0       # Very high RAM usage
            }
        ]
        
        scored_devices = self.service.device_scoring(extreme_data)
        
        # Ensure all devices are scored
        self.assertEqual(len(scored_devices), 2)
        
        # The first device should have a significantly higher score
        self.assertTrue(scored_devices[0]['score'] > scored_devices[1]['score'])
        
        # The score difference should be significant
        self.assertTrue(scored_devices[0]['score'] - scored_devices[1]['score'] > 50)
    
if __name__ == "__main__":
    unittest.main()

