import pytest
import json
from unittest.mock import patch, MagicMock
from bson import ObjectId
from django.test import Client, RequestFactory
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
    def test_delete_device_success(self, mock_remove_device, test_data):
        factory = RequestFactory()
        mock_remove_device.return_value = "success"
        data = {'device_name': test_data['device_name']}
        request = factory.post(
            f'/devices/delete_device/{test_data["username"]}/',
            data=json.dumps(data),
            content_type='application/json'
        )
        request.username_from_token = test_data['username']
        from apps.devices.views import delete_device
        response = delete_device(request)
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data == {'result': 'success', 'message': 'Device deleted successfully.'}
        mock_remove_device.assert_called_once_with(test_data['username'], test_data['device_name'])

    @patch('apps.devices.views.remove_device')
    def test_delete_device_failure(self, mock_remove_device, test_data):
        factory = RequestFactory()
        mock_remove_device.return_value = "error"
        data = {'device_name': test_data['device_name']}
        request = factory.post(
            f'/devices/delete_device/{test_data["username"]}/',
            data=json.dumps(data),
            content_type='application/json'
        )
        request.username_from_token = test_data['username']
        from apps.devices.views import delete_device
        response = delete_device(request)
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data == {'result': 'fail', 'message': 'error'}

    @patch('apps.devices.views.db_update_device_configuration_preferences')
    def test_update_device_configuration_preferences(self, mock_update_config, test_data):
        factory = RequestFactory()
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
        request = factory.post(
            f'/devices/update_device_configurations/{test_data["username"]}/',
            data=json.dumps(data),
            content_type='application/json'
        )
        request.username_from_token = test_data['username']
        from apps.devices.views import update_device_configuration_preferences
        response = update_device_configuration_preferences(request)
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data == {
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

    @patch('apps.devices.declare_device_online.get_mongodb_collection')
    def test_declare_device_online_success(self, mock_get_collection, test_data, sample_user_data, sample_device_data):
        """Test successfully declaring a device online"""
        from apps.devices.declare_device_online import declare_device_online
        
        # Mock collections
        mock_users = MagicMock()
        mock_devices = MagicMock()
        
        # Setup collection mapping
        def get_collection_side_effect(collection_name):
            if collection_name == 'users':
                return mock_users
            elif collection_name == 'devices':
                return mock_devices
            return MagicMock()
        
        mock_get_collection.side_effect = get_collection_side_effect
        
        # Setup mock returns
        mock_users.find_one.return_value = sample_user_data
        mock_devices.find_one.return_value = sample_device_data
        
        # Setup mock update result
        mock_update_result = MagicMock()
        mock_update_result.modified_count = 1
        mock_devices.update_one.return_value = mock_update_result
        
        # Call the function
        result = declare_device_online(test_data['username'], test_data['device_name'])
        
        # Check result
        assert result['result'] == 'success'
        assert result['username'] == test_data['username']
        assert result['device_id'] == str(sample_device_data['_id'])
        
        # Verify that the correct MongoDB calls were made
        mock_users.find_one.assert_called_once_with({'username': test_data['username']})
        mock_devices.find_one.assert_called_once_with({
            'user_id': sample_user_data['_id'], 
            'device_name': test_data['device_name']
        })
        mock_devices.update_one.assert_called_once_with(
            {'_id': sample_device_data['_id']},
            {'$set': {'online': True}},
            upsert=True
        )

    @patch('apps.devices.declare_device_online.get_mongodb_collection')
    def test_declare_device_online_user_not_found(self, mock_get_collection, test_data):
        """Test declare device online when user is not found"""
        from apps.devices.declare_device_online import declare_device_online
        
        # Mock collections
        mock_users = MagicMock()
        mock_devices = MagicMock()
        
        # Setup collection mapping
        def get_collection_side_effect(collection_name):
            if collection_name == 'users':
                return mock_users
            elif collection_name == 'devices':
                return mock_devices
            return MagicMock()
        
        mock_get_collection.side_effect = get_collection_side_effect
        
        # Setup mock returns - user not found
        mock_users.find_one.return_value = None
        
        # Call the function
        result = declare_device_online(test_data['username'], test_data['device_name'])
        
        # Check result
        assert result['result'] == 'error'
        assert result['message'] == 'User not found'
        
        # Verify that only the user find call was made
        mock_users.find_one.assert_called_once_with({'username': test_data['username']})
        mock_devices.find_one.assert_not_called()
        mock_devices.update_one.assert_not_called()

    @patch('apps.devices.declare_device_online.get_mongodb_collection')
    def test_declare_device_online_device_not_found(self, mock_get_collection, test_data, sample_user_data):
        """Test declare device online when device is not found"""
        from apps.devices.declare_device_online import declare_device_online
        
        # Mock collections
        mock_users = MagicMock()
        mock_devices = MagicMock()
        
        # Setup collection mapping
        def get_collection_side_effect(collection_name):
            if collection_name == 'users':
                return mock_users
            elif collection_name == 'devices':
                return mock_devices
            return MagicMock()
        
        mock_get_collection.side_effect = get_collection_side_effect
        
        # Setup mock returns
        mock_users.find_one.return_value = sample_user_data
        mock_devices.find_one.return_value = None
        
        # Call the function
        result = declare_device_online(test_data['username'], test_data['device_name'])
        
        # Check result
        assert result['result'] == 'error'
        assert result['message'] == 'Device not found'
        
        # Verify that the correct MongoDB calls were made
        mock_users.find_one.assert_called_once_with({'username': test_data['username']})
        mock_devices.find_one.assert_called_once_with({
            'user_id': sample_user_data['_id'], 
            'device_name': test_data['device_name']
        })
        mock_devices.update_one.assert_not_called()

    @patch('apps.devices.declare_device_offline.get_mongodb_collection')
    def test_declare_device_offline_success(self, mock_get_collection, test_data, sample_user_data, sample_device_data):
        """Test successfully declaring a device offline"""
        from apps.devices.declare_device_offline import declare_device_offline
        
        # Mock collections
        mock_users = MagicMock()
        mock_devices = MagicMock()
        
        # Setup collection mapping
        def get_collection_side_effect(collection_name):
            if collection_name == 'users':
                return mock_users
            elif collection_name == 'devices':
                return mock_devices
            return MagicMock()
        
        mock_get_collection.side_effect = get_collection_side_effect
        
        # Setup mock returns
        mock_users.find_one.return_value = sample_user_data
        mock_devices.find_one.return_value = sample_device_data
        
        # Call the function
        result = declare_device_offline(test_data['username'], test_data['device_name'])
        
        # Check result
        assert result['result'] == 'success'
        assert result['username'] == test_data['username']
        
        # Verify that the correct MongoDB calls were made
        mock_users.find_one.assert_called_once_with({'username': test_data['username']})
        mock_devices.find_one.assert_called_once_with({
            'user_id': sample_user_data['_id'], 
            'device_name': test_data['device_name']
        })
        mock_devices.update_one.assert_called_once_with(
            {'_id': sample_device_data['_id']},
            {'$set': {'online': False}}
        )

    @patch('apps.devices.declare_device_offline.get_mongodb_collection')
    def test_declare_device_offline_user_not_found(self, mock_get_collection, test_data):
        """Test declare device offline when user is not found"""
        from apps.devices.declare_device_offline import declare_device_offline
        
        # Mock collections
        mock_users = MagicMock()
        mock_devices = MagicMock()
        
        # Setup collection mapping
        def get_collection_side_effect(collection_name):
            if collection_name == 'users':
                return mock_users
            elif collection_name == 'devices':
                return mock_devices
            return MagicMock()
        
        mock_get_collection.side_effect = get_collection_side_effect
        
        # Setup mock returns - user not found
        mock_users.find_one.return_value = None
        
        # Call the function
        result = declare_device_offline(test_data['username'], test_data['device_name'])
        
        # Check result
        assert result == "User not found"
        
        # Verify that only the user find call was made
        mock_users.find_one.assert_called_once_with({'username': test_data['username']})
        mock_devices.find_one.assert_not_called()
        mock_devices.update_one.assert_not_called()

    @patch('apps.devices.declare_device_offline.get_mongodb_collection')
    def test_declare_device_offline_device_not_found(self, mock_get_collection, test_data, sample_user_data):
        """Test declare device offline when device is not found"""
        from apps.devices.declare_device_offline import declare_device_offline
        
        # Mock collections
        mock_users = MagicMock()
        mock_devices = MagicMock()
        
        # Setup collection mapping
        def get_collection_side_effect(collection_name):
            if collection_name == 'users':
                return mock_users
            elif collection_name == 'devices':
                return mock_devices
            return MagicMock()
        
        mock_get_collection.side_effect = get_collection_side_effect
        
        # Setup mock returns
        mock_users.find_one.return_value = sample_user_data
        mock_devices.find_one.return_value = None
        
        # Call the function
        result = declare_device_offline(test_data['username'], test_data['device_name'])
        
        # Check result
        assert result == "Device not found"
        
        # Verify that the correct MongoDB calls were made
        mock_users.find_one.assert_called_once_with({'username': test_data['username']})
        mock_devices.find_one.assert_called_once_with({
            'user_id': sample_user_data['_id'], 
            'device_name': test_data['device_name']
        })
        mock_devices.update_one.assert_not_called()

    @patch('apps.devices.declare_device_offline.get_mongodb_collection')
    def test_declare_device_offline_update_error(self, mock_get_collection, test_data, sample_user_data, sample_device_data):
        """Test declare device offline when update throws an error"""
        from apps.devices.declare_device_offline import declare_device_offline
        
        # Mock collections
        mock_users = MagicMock()
        mock_devices = MagicMock()
        
        # Setup collection mapping
        def get_collection_side_effect(collection_name):
            if collection_name == 'users':
                return mock_users
            elif collection_name == 'devices':
                return mock_devices
            return MagicMock()
        
        mock_get_collection.side_effect = get_collection_side_effect
        
        # Setup mock returns
        mock_users.find_one.return_value = sample_user_data
        mock_devices.find_one.return_value = sample_device_data
        mock_devices.update_one.side_effect = Exception("Database error")
        
        # Call the function
        result = declare_device_offline(test_data['username'], test_data['device_name'])
        
        # Check result
        assert result == "Error updating device status"
        
        # Verify that the correct MongoDB calls were made
        mock_users.find_one.assert_called_once_with({'username': test_data['username']})
        mock_devices.find_one.assert_called_once_with({
            'user_id': sample_user_data['_id'], 
            'device_name': test_data['device_name']
        })
        mock_devices.update_one.assert_called_once_with(
            {'_id': sample_device_data['_id']},
            {'$set': {'online': False}}
        )
