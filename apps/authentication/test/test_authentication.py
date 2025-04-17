import pytest
import json
import bcrypt
from unittest.mock import patch, MagicMock
from django.test import Client
from django.urls import reverse
from bson.objectid import ObjectId
from pymongo.results import InsertOneResult, UpdateResult

@pytest.fixture
def client():
    return Client()

@pytest.fixture
def mock_mongodb():
    with patch('apps.authentication.views.MongoClient') as mock_client:
        # Setup mock collections
        mock_db = MagicMock()
        mock_client.return_value.__getitem__.return_value = mock_db
        
        # Mock collections
        mock_users = MagicMock()
        
        mock_db.__getitem__.side_effect = lambda x: {
            'users': mock_users
        }[x]
        
        yield {
            'client': mock_client,
            'db': mock_db,
            'users': mock_users
        }

@pytest.fixture
def mock_user_data():
    # Create a hashed password for testing
    password = "testpassword"
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    return {
        "_id": ObjectId("60d21b4667d0d8992e610c85"),
        "username": "testuser",
        "email": "test@example.com",
        "first_name": "Test",
        "last_name": "User",
        "phone_number": "123-456-7890",
        "password": hashed_password
    }

@pytest.mark.django_db
class TestAuthentication:
    def test_login_api_invalid_json(self, client):
        # Make request with invalid JSON
        url = reverse('login_api')
        response = client.post(
            url,
            data='invalid json',
            content_type='application/json'
        )
        
        # Assertions
        assert response.status_code == 400
        response_data = json.loads(response.content)
        assert 'error' in response_data

@pytest.mark.django_db
class TestRegistration:
    def test_register_invalid_json(self, client):
        # Make request with invalid JSON
        url = reverse('register')
        response = client.post(
            url,
            data='invalid json',
            content_type='application/json'
        )
        
        # Assertions
        assert response.status_code == 400
        response_data = json.loads(response.content)
        assert 'error' in response_data

@pytest.mark.django_db
class TestGoogleAuth:
    @patch('apps.authentication.views.flow')
    def test_google_auth_url(self, mock_flow, client):
        # Setup mock
        mock_flow.authorization_url.return_value = ('https://accounts.google.com/oauth2/test', None)
        
        # Make request
        url = reverse('google')
        response = client.get(url)
        
        # Assertions
        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert 'authUrl' in response_data
        assert response_data['authUrl'] == 'https://accounts.google.com/oauth2/test'
        
        # Verify mock call
        mock_flow.authorization_url.assert_called_once()

    @patch('apps.authentication.views.flow')
    @patch('apps.authentication.views.id_token')
    def test_google_callback_success(self, mock_id_token, mock_flow, client):
        # Setup mocks
        mock_credentials = MagicMock()
        mock_credentials.id_token = 'test_id_token'
        mock_flow.fetch_token.return_value = None
        mock_flow.credentials = mock_credentials
        
        mock_id_token.verify_oauth2_token.return_value = {
            'email': 'google@example.com',
            'name': 'Google User',
            'given_name': 'Google',
            'family_name': 'User',
            'picture': 'https://example.com/profile.jpg'
        }
        
        # Make request
        url = reverse('google_callback')
        response = client.get(f'{url}?code=test_code')
        
        # Assertions
        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert response_data['success'] is True
        assert 'user' in response_data
        assert response_data['user']['email'] == 'google@example.com'
        
        # Verify mock calls
        mock_flow.fetch_token.assert_called_once_with(code='test_code')
        mock_id_token.verify_oauth2_token.assert_called_once()

    def test_google_callback_no_code(self, client):
        # Make request with no code
        url = reverse('google_callback')
        response = client.get(url)
        
        # Assertions
        assert response.status_code == 400
        response_data = json.loads(response.content)
        assert response_data['success'] is False
        assert 'No authorization code provided' in response_data['error'] 
