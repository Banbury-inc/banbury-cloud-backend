import time
import threading
from datetime import datetime
from pymongo.mongo_client import MongoClient

# MongoDB connection
uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(uri)
db = client["NeuraNet"]
api_usage_collection = db["api_usage_logs"]


class AnalyticsTrackingMiddleware:
    """
    Middleware to track API usage including endpoint, method, user, response time, and status code.
    Uses async logging to avoid blocking requests.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Skip tracking for analytics endpoints themselves to avoid recursion
        excluded_paths = [
            '/analytics/',
        ]
        
        for path in excluded_paths:
            if request.path.startswith(path):
                return self.get_response(request)
        
        # Start timing
        start_time = time.time()
        
        # Get request info
        endpoint = request.path
        method = request.method
        username = getattr(request, 'username_from_token', None)
        if not username:
            user = getattr(request, 'user', None)
            if user and hasattr(user, 'username'):
                username = user.username
        
        # Process request
        response = self.get_response(request)
        
        # Calculate response time
        response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        status_code = response.status_code
        
        # Log asynchronously to avoid blocking
        self._log_async({
            'endpoint': endpoint,
            'method': method,
            'username': username,
            'response_time_ms': response_time,
            'status_code': status_code,
            'timestamp': datetime.utcnow(),
            'ip_address': self._get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
        })
        
        return response
    
    def _get_client_ip(self, request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def _log_async(self, log_data):
        """Log API usage data asynchronously to avoid blocking the request."""
        def log_to_db():
            try:
                api_usage_collection.insert_one(log_data)
            except Exception as e:
                # Silently fail to avoid breaking the application
                print(f"Error logging API usage: {e}")
        
        # Run in a separate thread
        thread = threading.Thread(target=log_to_db)
        thread.daemon = True
        thread.start()

