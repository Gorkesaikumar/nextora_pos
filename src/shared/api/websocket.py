"""WebSocket JWT Authentication middleware."""
import logging
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser

logger = logging.getLogger("nextora.api.websocket")


@database_sync_to_async
def get_user_from_token(token_key):
    """Validate the JWT token and return the user."""
    try:
        from rest_framework_simplejwt.authentication import JWTAuthentication
        
        jwt_auth = JWTAuthentication()
        validated_token = jwt_auth.get_validated_token(token_key)
        user = jwt_auth.get_user(validated_token)
        return user
    except Exception as e:
        logger.warning(f"WebSocket JWT validation failed: {e}")
        return AnonymousUser()


class TokenAuthMiddleware(BaseMiddleware):
    """
    Middleware that parses a JWT token from the query string and populates scope["user"].
    Used for mobile apps (Flutter) connecting to Django Channels.
    """
    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode()
        query_params = parse_qs(query_string)
        token = query_params.get("token", [None])[0]
        
        if token:
            user = await get_user_from_token(token)
            if user and not isinstance(user, AnonymousUser):
                # If we successfully parsed a token, set it. Otherwise leave the 
                # AuthMiddlewareStack's resolution (session based) intact.
                scope["user"] = user
                
        return await super().__call__(scope, receive, send)
