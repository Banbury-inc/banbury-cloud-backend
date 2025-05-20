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
            '/authentication/auth/callback/'
        ]
        
        # Check if the current path starts with any of the excluded paths
        for path in excluded_paths:
            if path == '/':
                if request.path == '/':
                    return self.get_response(request)
            elif request.path.startswith(path.rstrip('/')):
                return self.get_response(request)

        # Validate API key
        api_key = request.headers.get('X-API-Key')
        if not hasattr(settings, 'API_KEYS') or not settings.API_KEYS:
            # Skip API key validation if API_KEYS is not configured
            pass
        elif not api_key:
            return JsonResponse({'detail': 'API key required'}, status=401)
        elif api_key not in settings.API_KEYS:
            return JsonResponse({'detail': 'Invalid API key'}, status=401)

        # Validate JWT token
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return JsonResponse({'detail': 'Not authorized'}, status=401)
        
        # Extract the token
        if ' ' not in auth_header:
            return JsonResponse({'detail': 'Invalid token format'}, status=401)

        auth_type, token = auth_header.split(' ', 1)
        if auth_type.lower() != 'bearer':
            return JsonResponse({'detail': 'Invalid token type'}, status=401)

        # Validate the token
        try:
            validated = AccessToken(token)  # Instantiation validates
        except TokenError as e:
            # Token-specific error – invalid, expired, etc.
            return JsonResponse({'detail': str(e)}, status=401)

        # Attach claims to request for later use
        # AccessToken exposes its content via the `payload` attribute (a standard dict).
        request.jwt_payload = validated.payload

        # Convenience: surface the username claim if present
        username_claim = request.jwt_payload.get('username')
        if username_claim:
            request.username_from_token = username_claim

        # Token is valid – allow the request to proceed to the view
        return self.get_response(request)