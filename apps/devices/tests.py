from django.test import TestCase, Client
from django.urls import reverse
import json
from unittest.mock import patch, MagicMock
from bson import ObjectId

class DeviceViewsTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Test data
        self.username = 'testuser'
        self.device_name = 'test_device'
        self.mock_user_id = ObjectId('507f1f77bcf86cd799439011')
        self.mock_device_id = ObjectId('507f1f77bcf86cd799439022')
    @patch('apps.devices.views.remove_device')
    def test_delete_device_success(self, mock_remove_device):
        """Test successfully deleting a device"""
        # Mock successful device removal
        mock_remove_device.return_value = "success"
        
        # Delete request data
        data = {'device_name': self.device_name}
        
        # Make request with correct URL
        response = self.client.post(
            f'/devices/delete_device/{self.username}/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'result': 'success', 'message': 'Device deleted successfully.'})
        
        # Verify call to remove_device
        mock_remove_device.assert_called_once_with(self.username, self.device_name)
        
    @patch('apps.devices.views.remove_device')
    def test_delete_device_failure(self, mock_remove_device):
        """Test failure when deleting a device"""
        # Mock failed device removal
        mock_remove_device.return_value = "error"
        
        # Delete request data
        data = {'device_name': self.device_name}
        
        # Make request with correct URL
        response = self.client.post(
            f'/devices/delete_device/{self.username}/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'result': 'fail', 'message': 'Device not deleted.'})
        
    @patch('apps.devices.views.db_update_device_configuration_preferences')
    def test_update_device_configuration_preferences(self, mock_update_config):
        """Test updating device configuration preferences"""
        # Mock successful update with returned data
        mock_update_config.return_value = {
            'device_name': self.device_name,
            'configurations': {
                'use_device_in_file_sync': True,
                'use_predicted_cpu_usage': True,
                'use_predicted_gpu_usage': False,
                'use_predicted_ram_usage': True,
                'use_predicted_download_speed': True,
                'use_predicted_upload_speed': True,
                'use_files_needed': False,
                'use_files_available_for_download': True
            }
        }
        
        # Configuration data
        data = {
            'device_name': self.device_name,
            'use_device_in_file_sync': True,
            'use_predicted_cpu_usage': True,
            'use_predicted_gpu_usage': False,
            'use_predicted_ram_usage': True,
            'use_predicted_download_speed': True,
            'use_predicted_upload_speed': True,
            'use_files_needed': False,
            'use_files_available_for_download': True
        }
        
        # Make request with correct URL
        response = self.client.post(
            f'/devices/update_device_configurations/{self.username}/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            'result': 'success',
            'data': {
                'device_name': self.device_name,
                'configurations': {
                    'use_device_in_file_sync': True,
                    'use_predicted_cpu_usage': True,
                    'use_predicted_gpu_usage': False,
                    'use_predicted_ram_usage': True,
                    'use_predicted_download_speed': True,
                    'use_predicted_upload_speed': True,
                    'use_files_needed': False,
                    'use_files_available_for_download': True
                }
            }
        })
        
        # Verify call to update function
        mock_update_config.assert_called_once_with(
            self.username, 
            self.device_name, 
            {
                'use_device_in_file_sync': True,
                'use_predicted_cpu_usage': True,
                'use_predicted_gpu_usage': False,
                'use_predicted_ram_usage': True,
                'use_predicted_download_speed': True,
                'use_predicted_upload_speed': True,
                'use_files_needed': False,
                'use_files_available_for_download': True
            }
        ) 
