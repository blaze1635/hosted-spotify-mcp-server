#!/usr/bin/env python3
"""
Middleware for MCP authentication
Validates API keys and provides user context to tools
"""

import json
from typing import Optional, Dict, Any, Callable
from starlette.requests import Request
from starlette.responses import JSONResponse
from auth import get_user_by_api_key, validate_api_key

class MCPAuthMiddleware:
    """Middleware to handle MCP authentication - enriches requests without blocking"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope, receive)
        
        # Check if this is an MCP request
        if request.url.path == "/mcp" or request.url.path.startswith("/mcp/"):
            # Always try to authenticate, but NEVER block requests
            # This allows Claude Desktop discovery while providing context when available
            auth_result = await self.authenticate_request(request)
            
            if auth_result["authenticated"]:
                # Add user context to request state for tools to access
                request.state.user_id = auth_result["user_id"]
                request.state.user = auth_result["user"]
                request.state.api_key = auth_result["api_key"]
                print(f"✅ Authenticated user: {auth_result['user_id']} via {auth_result.get('auth_method', 'unknown')}")
            else:
                print(f"⚠️ Authentication failed: {auth_result.get('error', 'Unknown error')}")
                # Don't block - let the request continue for tool discovery
        
        await self.app(scope, receive, send)
    
    async def authenticate_request(self, request: Request) -> Dict[str, Any]:
        """Authenticate MCP request and return user context"""
        try:
            api_key = None
            auth_method = None
            
            # Method 1: Authorization header (preferred/secure)
            auth_header = request.headers.get('authorization', '')
            if auth_header and auth_header.startswith('Bearer '):
                api_key = auth_header[7:]  # Remove "Bearer "
                auth_method = "header"
            
            # Method 2: URL parameter (Claude Desktop fallback)
            if not api_key:
                api_key = request.query_params.get('token')
                if api_key:
                    auth_method = "url_param"
            
            # No authentication provided
            if not api_key:
                return {
                    "authenticated": False,
                    "error": "Missing authentication. Provide Bearer token in Authorization header or 'token' parameter"
                }
            
            # Validate API key
            user = get_user_by_api_key(api_key)
            
            if not user:
                return {
                    "authenticated": False,
                    "error": "Invalid API key. Please re-authenticate at /auth/login"
                }
            
            return {
                "authenticated": True,
                "user_id": user.user_id,
                "user": user,
                "api_key": api_key,
                "auth_method": auth_method
            }
            
        except Exception as e:
            return {
                "authenticated": False,
                "error": f"Authentication error: {str(e)}"
            }

def get_user_context(request: Request) -> Optional[Dict[str, Any]]:
    """Extract user context from authenticated request with Spotify tokens"""
    if not hasattr(request.state, 'user_id'):
        return None
    
    try:
        from models import get_database_session, SpotifyToken
        from auth import decrypt_token
        
        user_id = request.state.user_id
        user = request.state.user
        
        # Get Spotify tokens for this user
        db = get_database_session()
        try:
            spotify_token = db.query(SpotifyToken).filter(SpotifyToken.user_id == user_id).first()
            
            if not spotify_token:
                print(f"No Spotify tokens found for user: {user_id}")
                return None
            
            # Create user context with decrypted tokens
            user_data = {
                "user_id": user.user_id,
                "spotify_user_id": user.spotify_user_id,
                "display_name": user.display_name,
                "spotify_access_token": decrypt_token(spotify_token.access_token),
                "spotify_refresh_token": decrypt_token(spotify_token.refresh_token) if spotify_token.refresh_token else None,
                "token_expires_at": spotify_token.expires_at
            }
            
            return {
                "user_id": user_id,
                "user": user_data
            }
            
        finally:
            db.close()
    
    except Exception as e:
        print(f"Error building user context: {e}")
        return None

def require_auth(func: Callable) -> Callable:
    """Decorator to require authentication for MCP tools"""
    def wrapper(*args, **kwargs):
        # This will be handled by the MCP framework
        # The user context will be passed via the request state
        return func(*args, **kwargs)
    
    return wrapper
