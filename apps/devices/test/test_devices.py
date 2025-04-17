import pytest
import json
from unittest.mock import patch, MagicMock
from bson import ObjectId
from django.test import Client
from django.urls import reverse
from pymongo.results import UpdateResult, DeleteResult

@pytest.fixture
def client():
    return Client()

@pytest.fixture
def test_data():
    return {
        'username': 'testuser',
        'device_name': 'test_device',
        'mock_user_id': ObjectId('507f1f77bcf86cd799439011'),
        'mock_device_id': ObjectId('507f1f77bcf86cd799439022')
    }

@pytest.fixture
def mock_mongodb():
    with patch('apps.devices.views.MongoClient') as mock_client:
        # Setup mock collections
        mock_db = MagicMock()
        mock_client.return_value.__getitem__.return_value = mock_db
        
        # Mock collections
        mock_devices = MagicMock()
        mock_users = MagicMock()
        
        mock_db.__getitem__.side_effect = lambda x: {
            'devices': mock_devices,
            'users': mock_users
        }[x]
        
        yield {
            'client': mock_client,
            'db': mock_db,
            'devices': mock_devices,
            'users': mock_users
        }

@pytest.fixture
def sample_device_data():
    return {
        "_id": ObjectId("507f1f77bcf86cd799439022"),
        "device_name": "test_device",
        "user_id": ObjectId("507f1f77bcf86cd799439011"),
        "device_type": "desktop",
        "is_online": True,
        "is_registered": True,
        "os": "Windows",
        "ip_address": "192.168.1.100",
        "storage": {
            "total": 500000,
            "used": 250000,
            "free": 250000
        },
        "configurations": {
            "use_device_in_file_sync": True,
            "use_predicted_cpu_usage": True,
            "use_predicted_gpu_usage": False,
            "use_predicted_ram_usage": True,
            "use_predicted_download_speed": True,
            "use_predicted_upload_speed": True,
            "use_files_needed": False,
            "use_files_available_for_download": True
        }
    }

@pytest.fixture
def sample_user_data():
    return {
        "_id": ObjectId("507f1f77bcf86cd799439011"),
        "username": "testuser",
        "email": "test@example.com",
        "devices": [ObjectId("507f1f77bcf86cd799439022")]
    }

@pytest.mark.django_db
class TestDevices:
    @patch('apps.devices.views.remove_device')
    def test_delete_device_success(self, mock_remove_device, client, test_data):
        """Test successfully deleting a device"""
        # Mock successful device removal
        mock_remove_device.return_value = "success"
        
        # Delete request data
        data = {'device_name': test_data['device_name']}
        
        # Make request with correct URL
        response = client.post(
            f'/devices/delete_device/{test_data["username"]}/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Check response
        assert response.status_code == 200
        assert response.json() == {'result': 'success', 'message': 'Device deleted successfully.'}
        
        # Verify call to remove_device
        mock_remove_device.assert_called_once_with(test_data['username'], test_data['device_name'])
        
    @patch('apps.devices.views.remove_device')
    def test_delete_device_failure(self, mock_remove_device, client, test_data):
        """Test failure when deleting a device"""
        # Mock failed device removal
        mock_remove_device.return_value = "error"
        
        # Delete request data
        data = {'device_name': test_data['device_name']}
        
        # Make request with correct URL
        response = client.post(
            f'/devices/delete_device/{test_data["username"]}/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Check response
        assert response.status_code == 200
        assert response.json() == {'result': 'fail', 'message': 'Device not deleted.'}
        
    @patch('apps.devices.views.db_update_device_configuration_preferences')
    def test_update_device_configuration_preferences(self, mock_update_config, client, test_data):
        """Test updating device configuration preferences"""
        # Mock successful update with returned data
        mock_update_config.return_value = {
            'device_name': test_data['device_name'],
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
            'device_name': test_data['device_name'],
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
        response = client.post(
            f'/devices/update_device_configurations/{test_data["username"]}/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Check response
        assert response.status_code == 200
        assert response.json() == {
            'result': 'success',
            'data': {
                'device_name': test_data['device_name'],
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
        }
        
        # Verify call to update function
        mock_update_config.assert_called_once_with(
            test_data['username'], 
            test_data['device_name'], 
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
