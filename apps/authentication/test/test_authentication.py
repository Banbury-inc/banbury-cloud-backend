import pytest
import json
import bcrypt
from unittest.mock import patch, MagicMock, Mock
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
    @patch('apps.authentication.views.Flow.from_client_config')
    def test_google_auth_url(self, mock_flow_from_client_config, client):
        # Setup mock flow instance
        mock_flow_instance = Mock()
        mock_flow_instance.authorization_url.return_value = ('https://accounts.google.com/oauth2/test', None)
        mock_flow_from_client_config.return_value = mock_flow_instance
        
        # Make request
        url = reverse('google')
        response = client.get(url)
        
        # Assertions
        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert 'authUrl' in response_data
        assert response_data['authUrl'] == 'https://accounts.google.com/oauth2/test'
        
        # Verify mock calls
        mock_flow_from_client_config.assert_called_once()
        mock_flow_instance.authorization_url.assert_called_once_with(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )

    @patch('apps.authentication.views.Flow.from_client_config')
    def test_google_auth_url_with_custom_redirect_uri(self, mock_flow_from_client_config, client):
        # Setup mock flow instance
        mock_flow_instance = Mock()
        mock_flow_instance.authorization_url.return_value = ('https://accounts.google.com/oauth2/test', None)
        mock_flow_from_client_config.return_value = mock_flow_instance
        
        # Make request with custom redirect URI
        url = reverse('google')
        response = client.get(url + '?redirect_uri=http://localhost:3001/authentication/auth/callback')
        
        # Assertions
        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert 'authUrl' in response_data
        assert response_data['authUrl'] == 'https://accounts.google.com/oauth2/test'
        
        # Verify the flow was created with the custom redirect URI
        mock_flow_from_client_config.assert_called_once()
        call_args = mock_flow_from_client_config.call_args
        client_config = call_args[0][0]
        assert 'http://localhost:3001/authentication/auth/callback' in client_config['web']['redirect_uris']

    def test_google_auth_url_invalid_redirect_uri(self, client):
        # Make request with invalid redirect URI
        url = reverse('google')
        response = client.get(url + '?redirect_uri=http://malicious-site.com/callback')
        
        # Assertions
        assert response.status_code == 400
        response_data = json.loads(response.content)
        assert 'error' in response_data
        assert 'Invalid redirect URI' in response_data['error']

    def test_google_callback_no_code(self, client):
        # Make request with no code
        url = reverse('google_callback')
        response = client.get(url)
        
        # Assertions
        assert response.status_code == 400
        response_data = json.loads(response.content)
        assert response_data['success'] is False
        assert 'No authorization code provided' in response_data['error'] 


@pytest.mark.django_db
class TestGmailLabels:
    def test_gmail_labels_requires_auth(self, client):
        url = reverse('gmail_labels')
        response = client.get(url)
        assert response.status_code == 401

    @patch('apps.authentication.views.requests.get')
    @patch('apps.authentication.views._refresh_google_access_token_if_needed')
    @patch('apps.authentication.views._get_mongo_user_by_username')
    @patch('apps.authentication.views._require_auth_username')
    def test_gmail_labels_includes_user_labels(
        self,
        mock_require_auth_username,
        mock_get_mongo_user_by_username,
        mock_refresh_google_access_token_if_needed,
        mock_requests_get,
        client
    ):
        mock_require_auth_username.return_value = "testuser"
        mock_get_mongo_user_by_username.return_value = {
            "_id": ObjectId("60d21b4667d0d8992e610c85"),
            "username": "testuser",
            "google_drive_credentials": {"access_token": "token"}
        }
        mock_refresh_google_access_token_if_needed.return_value = ("ya29.test-token", None)

        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.text = "ok"
        mock_resp.json.return_value = {
            "labels": [
                {"id": "INBOX", "name": "INBOX", "type": "system"},
                {"id": "Label_123", "name": "My Custom", "type": "user"}
            ]
        }
        mock_requests_get.return_value = mock_resp

        url = reverse('gmail_labels')
        response = client.get(url)
        assert response.status_code == 200

        data = json.loads(response.content)
        assert "labels" in data
        assert any(l.get("type") == "user" and l.get("name") == "My Custom" for l in data["labels"])
