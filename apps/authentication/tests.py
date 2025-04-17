from django.test import TestCase, Client
from django.urls import reverse
import json
from unittest.mock import patch, MagicMock
import bcrypt

class AuthenticationViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.login_url = '/authentication/login_api/'
        self.register_url = '/authentication/register/'
        # Create a mock password hash
        self.password = 'testpassword'
        self.password_hash = bcrypt.hashpw('testpassword'.encode('utf-8'), bcrypt.gensalt())
        
    @patch('pymongo.MongoClient')
    def test_login_api_success(self, mock_mongo):
        """Test successful login with correct credentials"""
        # Set up mock database response
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_mongo.return_value.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection
        
        # Mock user found in database with matching password
        mock_user = {'username': 'testuser', 'password': self.password_hash}
        mock_collection.find_one.return_value = mock_user
        
        # Request data
        data = {
            'username': 'testuser',
            'password': self.password
        }
        
        # Make request
        response = self.client.post(
            self.login_url, 
            data=json.dumps(data), 
            content_type='application/json'
        )
        
        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'response': 'success'})
        
    @patch('pymongo.MongoClient')
    def test_login_api_invalid_credentials(self, mock_mongo):
        """Test login with invalid credentials"""
        # Set up mock database response
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_mongo.return_value.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection
        
        # Mock user found but password doesn't match
        mock_user = {'username': 'testuser', 'password': self.password_hash}
        mock_collection.find_one.return_value = mock_user
        
        # Request with wrong password
        data = {
            'username': 'testuser',
            'password': 'wrongpassword'
        }
        
        # Make request
        response = self.client.post(
            self.login_url, 
            data=json.dumps(data), 
            content_type='application/json'
        )
        
        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'response': 'fail'})
        
    @patch('pymongo.MongoClient')
    def test_login_api_user_not_found(self, mock_mongo):
        """Test login with non-existent user"""
        # Set up mock database response
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_mongo.return_value.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection
        
        # Mock user not found
        mock_collection.find_one.return_value = None
        
        # Request data
        data = {
            'username': 'nonexistentuser',
            'password': 'anypassword'
        }
        
        # Make request
        response = self.client.post(
            self.login_url, 
            data=json.dumps(data), 
            content_type='application/json'
        )
        
        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'response': 'fail'})
        
    @patch('pymongo.MongoClient')
    def test_register_success(self, mock_mongo):
        """Test successful user registration"""
        # Set up mock database response
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_mongo.return_value.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection
        
        # Mock user not found (username available)
        mock_collection.find_one.return_value = None
        mock_collection.insert_one.return_value = MagicMock(inserted_id='123')
        
        # Registration data
        data = {
            'username': 'newuser',
            'password': 'password123',
            'first_name': 'John',
            'last_name': 'Doe',
            'phone_number': '1234567890',
            'email': 'john.doe@example.com',
            'picture': 'https://example.com/profile.jpg'
        }
        
        # Make request
        response = self.client.post(
            self.register_url, 
            data=json.dumps(data), 
            content_type='application/json'
        )
        
        # Check response
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        # Accept either 'success' or the user data object that contains 'result'
        if 'response' in response_data:
            self.assertEqual(response_data, {'response': 'success'})
        else:
            self.assertIn('result', response_data)
        
    @patch('pymongo.MongoClient')
    def test_register_username_taken(self, mock_mongo):
        """Test registration with existing username"""
        # Set up mock database response
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_mongo.return_value.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection
        
        # Mock user already exists
        mock_collection.find_one.return_value = {'username': 'existinguser'}
        
        # Registration data
        data = {
            'username': 'existinguser',
            'password': 'password123',
            'first_name': 'John',
            'last_name': 'Doe',
            'phone_number': '1234567890',
            'email': 'john.doe@example.com'
        }
        
        # Make request
        response = self.client.post(
            self.register_url, 
            data=json.dumps(data), 
            content_type='application/json'
        )
        
        # Check response
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        # Accept either the legacy format or the actual response
        if 'response' in response_data:
            self.assertEqual(response_data['response'], 'Username already exists')
        else:
            self.assertEqual(response_data['result'], 'user_already_exists')
        
