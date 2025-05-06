import jwt
from django.conf import settings
from django.http import JsonResponse
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken
import re
import traceback

class JWTAuthenticationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # Define paths that don't need authentication
        self.public_paths = [
            r'^/authentication/token/',
            r'^/authentication/login_api/',
            r'^/authentication/login/',
            r'^/authentication/register/',
            r'^/authentication/google/',
            r'^/authentication/auth/callback/',
            r'^/health/',
            r'^/docs/',
            r'^/static/',
            r'^/ws/',
            r'^/admin/',
            r'^/authentication/add_site_visitor_info/',
        ]

    def __call__(self, request):
        # Check if path is public
        path = request.path_info
        if any(re.match(pattern, path) for pattern in self.public_paths):
            return self.get_response(request)

        # Check for token in the Authorization header
        auth_header = request.headers.get('Authorization', '')
        print(f"request headers: {request.headers}")
        if not auth_header.startswith('Bearer '):
            # Check if we have X-Username header as a fallback for specific endpoints
            if request.headers.get('X-Username'):
                print(f"Using X-Username header for authentication: {request.headers.get('X-Username')}")
                # Set the username on the request object for views to use
                request.username = request.headers.get('X-Username')
                return self.get_response(request)
            
            return JsonResponse(
                {"error": "Authentication required"}, 
                status=401
            )

        token = auth_header.split(' ')[1]
        print(f"Token received: {token[:20]}...")
        
        try:
            # First try basic JWT decoding to see what's in the token
            try:
                # Try manual decoding first to debug
                decoded_payload = jwt.decode(token, options={"verify_signature": False})
                print(f"Raw decoded token payload (unverified): {decoded_payload}")
                if 'username' in decoded_payload:
                    print(f"Found username in raw token payload: {decoded_payload['username']}")
                else:
                    print("WARNING: No username found in the raw token payload")
            except Exception as e:
                print(f"Error during manual token decoding: {e}")
            
            # Now proceed with library validation
            token_obj = AccessToken(token)
            print(f"Token validated successfully with AccessToken: {token_obj}")
            
            # Extract user information from the token and set it on the request
            try:
                # Print the token payload
                decoded_token = token_obj.payload
                print(f"Token payload after validation: {decoded_token}")
                
                # Check for user identification in the token
                if 'username' in decoded_token:
                    request.username = decoded_token['username']
                    print(f"Set username from token: {request.username}")
                elif 'user_id' in decoded_token:
                    # If username not available, at least set the user_id
                    request.user_id = decoded_token['user_id']
                    print(f"Set user_id from token: {request.user_id}")
                else:
                    print("WARNING: Token validated but no username or user_id found in payload")
                    # Even if token is valid, we need to identify the user
                    if request.headers.get('X-Username'):
                        request.username = request.headers.get('X-Username')
                        print(f"Falling back to X-Username header: {request.username}")
                    else:
                        print("No username identification available - rejecting request")
                        return JsonResponse(
                            {"detail": "Token contained no recognizable user identification", "code": "token_not_valid"}, 
                            status=401
                        )
            except Exception as e:
                print(f"Error extracting user info from token: {e}")
                print(traceback.format_exc())  # Print full traceback
                # Fall back to X-Username header if available
                if request.headers.get('X-Username'):
                    request.username = request.headers.get('X-Username')
                    print(f"Falling back to X-Username header: {request.username}")
                else:
                    return JsonResponse(
                        {"detail": f"Error processing token: {str(e)}", "code": "token_not_valid"}, 
                        status=401
                    )
            
            # If we get here, the token is valid
            return self.get_response(request)
        except (InvalidToken, TokenError) as e:
            print(f"Token validation error: {e}")
            print(traceback.format_exc())  # Print full traceback
            
            # Try to use X-Username header as fallback for authentication
            if request.headers.get('X-Username'):
                print(f"Token validation failed, but using X-Username header as fallback: {request.headers.get('X-Username')}")
                # Set the username on the request object for views to use
                request.username = request.headers.get('X-Username')
                return self.get_response(request)
                
            return JsonResponse(
                {"detail": str(e), "code": "token_not_valid"}, 
                status=401
            ) 
