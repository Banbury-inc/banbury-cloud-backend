from channels.middleware import BaseMiddleware
from urllib.parse import parse_qs

class DeviceIdentificationMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        # Get query string and parse it properly
        query_string = scope.get("query_string", b"").decode()
        if query_string:
            query_params = parse_qs(query_string)
            # parse_qs returns a dict of lists, get first value if exists
            device_id = query_params.get('device_id', [None])[0]
            scope['device_id'] = device_id
        else:
            scope['device_id'] = None
        
        return await super().__call__(scope, receive, send) 