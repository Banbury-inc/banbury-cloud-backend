from django.http import JsonResponse
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken
from django.urls import resolve
from django.conf import settings

class AuthenticationTokenMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.jwt_authentication = JWTAuthentication()

    def __call__(self, request):
        # List of paths that don't require authentication
        if request.path.startswith('/authentication/getuserinfo4/'):
            return self.get_response(request)
            
        excluded_paths = [
            '/',
            '/authentication/login/',
            '/authentication/register/',
            '/authentication/new_register/',
            '/authentication/login_api/',
            '/authentication/google/',
            '/authentication/auth/callback/',
            # Public endpoints (no auth required)
            '/authentication/get_client_ip/',
            '/authentication/add_site_visitor_info/',
            '/authentication/get_site_visitor_info/',
            # X (Twitter) OAuth callback must be public
            '/authentication/x_api/oauth_callback/',
            # Slack OAuth callback must be public
            '/authentication/slack/oauth_callback/',
            # favicon should not require auth
            '/favicon.ico'
        ]
        
        # Check if the current path starts with any of the excluded paths
        for path in excluded_paths:
            if path == '/':
                if request.path == '/':
                    return self.get_response(request)
            elif request.path.startswith(path.rstrip('/')):
                return self.get_response(request)

        # Prefer Bearer token auth: if a valid JWT is present, allow the request
        auth_header = request.headers.get('Authorization')
        if auth_header and ' ' in auth_header:
            auth_type, token = auth_header.split(' ', 1)
            if auth_type.lower() == 'bearer':
                try:
                    validated = AccessToken(token)  # Instantiation validates
                    # Attach claims to request for later use
                    request.jwt_payload = validated.payload
                    username_claim = request.jwt_payload.get('username')
                    if username_claim:
                        request.username_from_token = username_claim
                    # Valid JWT – proceed without requiring API key
                    return self.get_response(request)
                except TokenError:
                    # Invalid/expired token; fall through to API key validation
                    pass

        # If JWT not provided/valid, allow X-API-Key authentication (if configured)
        api_keys_configured = hasattr(settings, 'API_KEYS') and bool(settings.API_KEYS)
        if api_keys_configured:
            api_key = request.headers.get('X-API-Key')
            if not api_key:
                return JsonResponse({'detail': 'API key required'}, status=401)
            if api_key not in settings.API_KEYS:
                return JsonResponse({'detail': 'Invalid API key'}, status=401)
            # Valid API key – proceed
            return self.get_response(request)

        # Neither a valid JWT nor API key (and API keys not configured) – unauthorized
        return JsonResponse({'detail': 'Not authorized'}, status=401)