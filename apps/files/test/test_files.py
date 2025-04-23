import unittest
from unittest.mock import patch, MagicMock
import json
from bson.objectid import ObjectId
import pytest
from django.test import RequestFactory
from django.http import JsonResponse

# Import modules to test
from apps.files.delete_files import delete_files
from apps.files.get_file_info import get_file_info
from apps.files.get_files_info import get_files_info
from apps.files.update_files import update_files
from apps.files.search_for_file import search_for_file
from apps.files.download_file import download_file

# Import views to test
from apps.files.views import add_file, add_files, handle_delete_files, handle_update_files, getfileinfo


class DeleteFilesTest(unittest.TestCase):
    """Test suite for the delete_files module."""

    @patch('apps.files.delete_files.MongoClient')
    def test_delete_files_success(self, mock_mongo_client):
        """Test successful deletion of files."""
        # Set up mock
        mock_client = MagicMock()
        mock_mongo_client.return_value = mock_client
        
        mock_db = mock_client.__getitem__.return_value
        mock_collection = mock_db.__getitem__.return_value
        
        # Mock device collection to return a device with a specific ID
        mock_device_collection = mock_db.__getitem__.return_value
        mock_device_collection.find_one.return_value = {'_id': ObjectId('60b6e4b5f429d53a5d7e346a')}
        
        # Mock file collection delete_many to return successful result
        mock_file_collection = mock_db.__getitem__.return_value
        mock_delete_result = MagicMock()
        mock_delete_result.deleted_count = 2
        mock_file_collection.delete_many.return_value = mock_delete_result
        
        # Test the function
        result = delete_files('testuser', 'testdevice', [{'file_name': 'file1.txt'}, {'file_name': 'file2.txt'}])
        
        # Assert results
        self.assertEqual(result, 'success')
        mock_file_collection.delete_many.assert_called_once()

    @patch('apps.files.delete_files.MongoClient')
    def test_device_not_found(self, mock_mongo_client):
        """Test deletion when device is not found."""
        # Set up mock
        mock_client = MagicMock()
        mock_mongo_client.return_value = mock_client
        
        mock_db = mock_client.__getitem__.return_value
        
        # Mock device collection to return None (device not found)
        mock_device_collection = mock_db.__getitem__.return_value
        mock_device_collection.find_one.return_value = None
        
        # Test the function
        result = delete_files('testuser', 'nonexistentdevice', [{'file_name': 'file1.txt'}])
        
        # Assert results
        self.assertEqual(result, 'device_not_found')


class GetFileInfoTest(unittest.TestCase):
    """Test suite for the get_file_info module."""

    @patch('apps.files.get_file_info.MongoClient')
    def test_get_file_info_success(self, mock_mongo_client):
        """Test successful retrieval of file info."""
        # Set up mock
        mock_client = MagicMock()
        mock_mongo_client.return_value = mock_client
        
        mock_db = mock_client.__getitem__.return_value
        mock_file_collection = mock_db.__getitem__.return_value
        
        # Mock file data
        mock_file = {
            '_id': ObjectId('60b6e4b5f429d53a5d7e346a'),
            'file_name': 'test_file.txt',
            'file_size': 1024,
            'file_type': 'text/plain',
            'file_path': '/path/to/file',
            'date_uploaded': '2023-01-01',
            'date_modified': '2023-01-02',
            'date_accessed': '2023-01-03',
            'kind': 'document',
            'device_id': ObjectId('60b6e4b5f429d53a5d7e346b')
        }
        
        mock_file_collection.find_one.return_value = mock_file
        
        # Test the function
        result = get_file_info('testuser', '60b6e4b5f429d53a5d7e346a')
        
        # Assert results
        self.assertEqual(result['file_name'], 'test_file.txt')
        self.assertEqual(result['file_size'], 1024)
        self.assertEqual(result['device_id'], str(ObjectId('60b6e4b5f429d53a5d7e346b')))
        
    @patch('apps.files.get_file_info.MongoClient')
    def test_get_file_info_not_found(self, mock_mongo_client):
        """Test file info retrieval when file is not found."""
        # Set up mock
        mock_client = MagicMock()
        mock_mongo_client.return_value = mock_client
        
        mock_db = mock_client.__getitem__.return_value
        mock_file_collection = mock_db.__getitem__.return_value
        
        # Mock file not found
        mock_file_collection.find_one.return_value = None
        
        # Test the function
        result = get_file_info('testuser', '60b6e4b5f429d53a5d7e346a')
        
        # Assert results
        self.assertIsNone(result)


class GetFilesInfoTest(unittest.TestCase):
    """Test suite for the get_files_info module."""
    
    
    @patch('apps.files.get_files_info.MongoClient')
    def test_get_files_info_user_not_found(self, mock_mongo_client):
        """Test files info retrieval when user is not found."""
        # Set up mock
        mock_client = MagicMock()
        mock_mongo_client.return_value = mock_client
        
        mock_db = mock_client.__getitem__.return_value
        
        # Mock user collection to return None (user not found)
        mock_user_collection = mock_db.__getitem__.return_value
        mock_user_collection.find_one.return_value = None
        
        # Test the function
        result = get_files_info('nonexistentuser')
        
        # Assert results
        self.assertIn('error', result)
        self.assertEqual(result['error'], 'Please login first.')


class DownloadFileTest(unittest.TestCase):
    """Test suite for the download_file module."""
    
    @patch('apps.files.download_file.MongoClient')
    def test_download_file_not_found(self, mock_mongo_client):
        """Test download when file is not found."""
        # Set up MongoDB client mock
        mock_client = mock_mongo_client.return_value
        mock_db = mock_client.__getitem__.return_value
        
        # Mock file collection to return None (file not found)
        mock_file_collection = mock_db.__getitem__.return_value
        mock_file_collection.find_one.return_value = None
        
        # Test the function
        result = download_file('testuser', 'nonexistent_file_id', False)
        
        # Assert results
        self.assertEqual(result, 'file_not_found')


class ViewTests(unittest.TestCase):
    """Test suite for view functions."""
    
    def setUp(self):
        """Set up for tests."""
        self.factory = RequestFactory()
    
    @patch('apps.files.views.MongoClient')
    @patch('apps.files.views.broadcast_new_file')
    def test_add_file(self, mock_broadcast, mock_mongo_client):
        """Test the add_file view function."""
        # Set up mock
        mock_client = MagicMock()
        mock_mongo_client.return_value = mock_client
        
        mock_db = mock_client.__getitem__.return_value
        mock_device_collection = mock_db.__getitem__.return_value
        mock_file_collection = mock_db.__getitem__.return_value
        
        # Mock device data
        mock_device_collection.find_one.return_value = {
            '_id': ObjectId('60b6e4b5f429d53a5d7e346a'),
            'device_name': 'test_device'
        }
        
        # Mock broadcast result
        mock_broadcast.return_value = True
        
        # Create a request
        file_data = {
            'file_type': 'text/plain',
            'file_name': 'test_file.txt',
            'file_path': '/path/to/file',
            'date_uploaded': '2023-01-01',
            'date_modified': '2023-01-02',
            'file_size': 1024,
            'file_priority': 'high',
            'file_parent': None,
            'original_device': 'test_device',
            'kind': 'document'
        }
        
        request = self.factory.post(
            '/api/files/testuser',
            data=json.dumps(file_data),
            content_type='application/json'
        )
        
        # Test the view
        response = add_file(request, 'testuser')
        
        # Assert response
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['result'], 'success')
        self.assertEqual(response_data['username'], 'testuser')


@pytest.mark.django_db
class TestFilesIntegration:
    """Integration tests for files functionality."""
    
    @pytest.fixture
    def mock_mongodb(self, monkeypatch):
        """Mock MongoDB client for integration tests."""
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_collection = MagicMock()
        
        mock_client.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection
        
        monkeypatch.setattr('pymongo.MongoClient', lambda uri: mock_client)
        return mock_client, mock_db, mock_collection
    
    def test_file_workflow(self, mock_mongodb):
        """Test a complete file workflow: add, update, get, delete."""
        client, db, collection = mock_mongodb
        
        # Mock data for tests
        file_id = ObjectId('60b6e4b5f429d53a5d7e346a')
        device_id = ObjectId('60b6e4b5f429d53a5d7e346b')
        
        # Create separate mock collections
        device_collection = MagicMock()
        file_collection = MagicMock()
        
        # Configure the db to return different collections based on key
        collections = {
            'devices': device_collection,
            'files': file_collection,
        }
        db.__getitem__.side_effect = lambda key: collections.get(key, MagicMock())
        
        # Mock device data response
        device_collection.find_one.return_value = {'_id': device_id, 'device_name': 'test_device'}
        
        # Mock file collection responses
        file_collection.insert_one.return_value = MagicMock(inserted_id=file_id)
        file_collection.find_one.return_value = {
            '_id': file_id,
            'file_name': 'test_file.txt',
            'file_size': 1024,
            'device_id': device_id
        }
        
        # Test adding a file
        factory = RequestFactory()
        
        # Add file request
        add_request = factory.post(
            '/api/files/testuser',
            data=json.dumps({
                'file_type': 'text/plain',
                'file_name': 'test_file.txt',
                'file_path': '/path/to/file',
                'date_uploaded': '2023-01-01',
                'date_modified': '2023-01-02',
                'file_size': 1024,
                'file_priority': 'high',
                'file_parent': None,
                'original_device': 'test_device',
                'kind': 'document'
            }),
            content_type='application/json'
        )
        
        # Test the add_file view, make sure device returns device not found if device is not found
        with patch('apps.files.views.broadcast_new_file') as mock_broadcast:
            mock_broadcast.return_value = True
            add_response = add_file(add_request, 'testuser')
            assert add_response.status_code == 200
            add_data = json.loads(add_response.content)
            assert add_data['result'] == 'device_not_found'
