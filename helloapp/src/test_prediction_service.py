import unittest
from prediction_service import PredictionService
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

class TestPredictionService(unittest.TestCase):
    def setUp(self):
        self.service = PredictionService()
        
        # Create sample test data
        self.test_devices = [{
            'device_name': 'Test Device',
            'upload_network_speed': ['10.5', '11.0', '10.8', '11.2', '10.9'],
            'download_network_speed': ['50.5', '51.0', '50.8', '51.2', '50.9'],
            'gpu_usage': ['75.5', '76.0', '75.8', '76.2', '75.9'],
            'cpu_usage': ['65.5', '66.0', '65.8', '66.2', '65.9'],
            'ram_usage': ['85.5', '86.0', '85.8', '86.2', '85.9'],
            'date_added': [
                (datetime.now() - timedelta(hours=4)).strftime("%Y-%m-%d %H:%M:%S.%f"),
                (datetime.now() - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S.%f"),
                (datetime.now() - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S.%f"),
                (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S.%f"),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
            ]
        }]

    def test_create_dataset(self):
        # Test create_dataset method
        X = pd.DataFrame({'value': [1, 2, 3, 4, 5]})
        y = pd.DataFrame({'value': [1, 2, 3, 4, 5]})
        X_result, y_result = self.service.create_dataset(X, y, time_steps=2)
        
        self.assertEqual(X_result.shape[0], 3)  # Should have 3 samples with time_steps=2
        self.assertEqual(y_result.shape[0], 3)  # Should have 3 target values

    def test_performance_data(self):
        # Test performance_data method
        result = self.service.performance_data(self.test_devices, show_graph=False)
        
        # Check if result contains expected data
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)  # Should have one device's predictions
        
        device_prediction = result[0]
        self.assertIn('device_name', device_prediction)
        self.assertIn('predicted_upload_speed', device_prediction)
        self.assertIn('predicted_download_speed', device_prediction)
        self.assertIn('predicted_gpu_usage', device_prediction)
        self.assertIn('predicted_cpu_usage', device_prediction)
        self.assertIn('predicted_ram_usage', device_prediction)
        
        # Check if predictions are within reasonable ranges
        self.assertGreater(device_prediction['predicted_upload_speed'], 0)
        self.assertGreater(device_prediction['predicted_download_speed'], 0)
        self.assertGreaterEqual(device_prediction['predicted_gpu_usage'], 0)
        self.assertLessEqual(device_prediction['predicted_gpu_usage'], 100)
        self.assertGreaterEqual(device_prediction['predicted_cpu_usage'], 0)
        self.assertLessEqual(device_prediction['predicted_cpu_usage'], 100)
        self.assertGreaterEqual(device_prediction['predicted_ram_usage'], 0)
        self.assertLessEqual(device_prediction['predicted_ram_usage'], 100)

    def test_build_and_train_model(self):
        # Test model building and training
        X_train = np.random.rand(100, 5, 1)  # 100 samples, 5 time steps, 1 feature
        y_train = np.random.rand(100)
        
        model = self.service.build_and_train_model(X_train, y_train, time_steps=5, features=1)
        
        # Check if model has expected layers
        self.assertEqual(len(model.layers), 2)  # Should have LSTM and Dense layers
        
        # Test prediction shape
        test_input = np.random.rand(1, 5, 1)
        prediction = model.predict(test_input)
        self.assertEqual(prediction.shape, (1, 1))  # Should output a single prediction

if __name__ == '__main__':
    unittest.main()

