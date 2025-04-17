from django.test import TestCase, Client
from django.urls import reverse
import json
from unittest.mock import patch, MagicMock
from bson import ObjectId

class FilesViewsTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Test data
        self.username = 'testuser'
        self.device_name = 'test_device'
        self.mock_user_id = ObjectId('507f1f77bcf86cd799439011')
        self.mock_device_id = ObjectId('507f1f77bcf86cd799439022')
        self.mock_file_id = ObjectId('507f1f77bcf86cd799439033')
        
    @patch('pymongo.MongoClient')
    @patch('websocket.utils.broadcast_new_file')
    def test_add_file_success(self, mock_broadcast, mock_mongo):
        """Test successfully adding a file"""
        # Set up mock database response
        mock_db = MagicMock()
        mock_device_collection = MagicMock()
        mock_file_collection = MagicMock()
        mock_mongo.return_value.__getitem__.return_value = mock_db
        mock_db.__getitem__.side_effect = lambda x: mock_device_collection if x == 'devices' else mock_file_collection
        
        # Mock device found in database
        mock_device = {'_id': self.mock_device_id, 'device_name': self.device_name}
        mock_device_collection.find_one.return_value = mock_device
        
        # Mock successful file insertion
        mock_file_collection.insert_one.return_value = MagicMock(inserted_id=self.mock_file_id)
        
        # Mock successful broadcast
        mock_broadcast.return_value = True
        
        # File data
        data = {
            'file_type': 'text',
            'file_name': 'test.txt',
            'file_path': '/home/user/documents/test.txt',
            'date_uploaded': '2023-06-01T12:00:00',
            'date_modified': '2023-05-30T10:00:00',
            'file_size': 1024,
            'file_priority': 1,
            'file_parent': 'documents',
            'original_device': self.device_name,
            'kind': 'file'
        }
        
        # Make request with correct URL
        response = self.client.post(
            f'/files/add_file/{self.username}/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'result': 'success', 'username': self.username})
        
        # Verify calls to MongoDB and broadcast
        mock_device_collection.find_one.assert_called_once_with({'device_name': self.device_name})
        mock_file_collection.insert_one.assert_called_once()
        mock_broadcast.assert_called_once()
        
    @patch('pymongo.MongoClient')
    def test_add_file_device_not_found(self, mock_mongo):
        """Test adding a file with non-existent device"""
        # Set up mock database response
        mock_db = MagicMock()
        mock_device_collection = MagicMock()
        mock_mongo.return_value.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_device_collection
        
        # Mock device not found
        mock_device_collection.find_one.return_value = None
        
        # File data
        data = {
            'file_type': 'text',
            'file_name': 'test.txt',
            'file_path': '/home/user/documents/test.txt',
            'date_uploaded': '2023-06-01T12:00:00',
            'date_modified': '2023-05-30T10:00:00',
            'file_size': 1024,
            'file_priority': 1,
            'file_parent': 'documents',
            'original_device': 'nonexistent_device',
            'kind': 'file'
        }
        
        # Make request with correct URL
        response = self.client.post(
            f'/files/add_file/{self.username}/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'result': 'device_not_found', 'message': 'Device not found.'})
        
    @patch('pymongo.MongoClient')
    def test_add_files_success(self, mock_mongo):
        """Test successfully adding multiple files"""
        # Set up mock database response
        mock_db = MagicMock()
        mock_user_collection = MagicMock()
        mock_device_collection = MagicMock()
        mock_file_collection = MagicMock()
        mock_mongo.return_value.__getitem__.return_value = mock_db
        mock_db.__getitem__.side_effect = lambda x: {
            'users': mock_user_collection,
            'devices': mock_device_collection,
            'files': mock_file_collection
        }.get(x)
        
        # Mock user and device found in database
        mock_user = {'_id': self.mock_user_id, 'username': self.username}
        mock_user_collection.find_one.return_value = mock_user
        
        mock_device = {'_id': self.mock_device_id, 'device_name': self.device_name, 'user_id': self.mock_user_id}
        mock_device_collection.find_one.return_value = mock_device
        
        # Mock successful file insertion
        mock_file_collection.insert_many.return_value = MagicMock(inserted_ids=[self.mock_file_id, ObjectId()])
        
        # Files data
        data = {
            'device_name': self.device_name,
            'files': [
                {
                    'file_name': 'test1.txt',
                    'file_path': '/home/user/documents/test1.txt',
                    'file_type': 'text',
                    'file_size': 1024,
                    'date_uploaded': '2023-06-01T12:00:00',
                    'date_modified': '2023-05-30T10:00:00',
                    'file_parent': 'documents',
                    'original_device': self.device_name,
                    'kind': 'file'
                },
                {
                    'file_name': 'test2.txt',
                    'file_path': '/home/user/documents/test2.txt',
                    'file_type': 'text',
                    'file_size': 2048,
                    'date_uploaded': '2023-06-01T12:00:00',
                    'date_modified': '2023-05-30T10:00:00',
                    'file_parent': 'documents',
                    'original_device': self.device_name,
                    'kind': 'file'
                }
            ]
        }
        
        # Make request with correct URL
        response = self.client.post(
            f'/files/add_files/{self.username}/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'result': 'success', 'message': '2 files added successfully.'})
        
        # Verify calls to MongoDB
        mock_user_collection.find_one.assert_called_once_with({'username': self.username})
        mock_device_collection.find_one.assert_called_once_with({
            'device_name': self.device_name, 
            'user_id': self.mock_user_id
        })
        mock_file_collection.insert_many.assert_called_once()
        
    @patch('pymongo.MongoClient')
    def test_add_files_device_not_found(self, mock_mongo):
        """Test adding files with non-existent device"""
        # Set up mock database response
        mock_db = MagicMock()
        mock_user_collection = MagicMock()
        mock_device_collection = MagicMock()
        mock_mongo.return_value.__getitem__.return_value = mock_db
        mock_db.__getitem__.side_effect = lambda x: {
            'users': mock_user_collection,
            'devices': mock_device_collection
        }.get(x)
        
        # Mock user found but device not found
        mock_user = {'_id': self.mock_user_id, 'username': self.username}
        mock_user_collection.find_one.return_value = mock_user
        mock_device_collection.find_one.return_value = None
        
        # Files data
        data = {
            'device_name': 'nonexistent_device',
            'files': [
                {
                    'file_name': 'test1.txt',
                    'file_path': '/home/user/documents/test1.txt',
                    'file_type': 'text'
                }
            ]
        }
        
        # Make request with correct URL
        response = self.client.post(
            f'/files/add_files/{self.username}/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'result': 'device_not_found', 'message': 'Device not found.'})
        
    @patch('apps.files.views.delete_files')
    def test_handle_delete_files_success(self, mock_delete_files):
        """Test successfully deleting files"""
        # Mock successful file deletion
        mock_delete_files.return_value = {"result": "success", "count": 2}
        
        # Delete files data
        data = {
            'file_ids': [str(self.mock_file_id), str(ObjectId())]
        }
        
        # Make request with correct URL
        response = self.client.post(
            f'/files/delete_files/{self.username}/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'result': 'success', 'message': '2 files deleted successfully.'})
        
        # Verify call to delete_files
        mock_delete_files.assert_called_once_with(self.username, data['file_ids'])
        
    @patch('apps.files.views.delete_files')
    def test_handle_delete_files_failure(self, mock_delete_files):
        """Test failure when deleting files"""
        # Mock failed file deletion
        mock_delete_files.return_value = {"result": "error", "message": "Files not found"}
        
        # Delete files data
        data = {
            'file_ids': [str(self.mock_file_id), str(ObjectId())]
        }
        
        # Make request with correct URL
        response = self.client.post(
            f'/files/delete_files/{self.username}/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'result': 'error', 'message': 'Files not found'})
        
    def test_handle_delete_files_missing_file_ids(self):
        """Test delete files with missing file_ids field"""
        # Delete files data with missing file_ids
        data = {}
        
        # Make request with correct URL
        response = self.client.post(
            f'/files/delete_files/{self.username}/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Check response
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'error': 'Missing file_ids'}) 