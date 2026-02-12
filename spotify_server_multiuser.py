#!/usr/bin/env python3
"""
Hosted Spotify MCP Server - Multi-User Version
Supports multiple users with authentication and secure token storage
"""

import os
import json
from typing import Optional, Dict, Any

# Load environment variables FIRST, before any other imports
from dotenv import load_dotenv
load_dotenv()

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.middleware.sessions import SessionMiddleware
from starlette.routing import Mount
from starlette.applications import Starlette

# Import our modules
from models import init_database
from middleware import MCPAuthMiddleware, get_user_context
from web_auth import auth_routes
from spotify_tools import (
    search_tracks_impl, get_current_track_impl, get_user_playlists_impl,
    create_playlist_impl, add_tracks_to_playlist_impl, get_liked_songs_impl,
    get_playlist_tracks_impl, get_spotify_status_impl
)
from auth import cleanup_expired_sessions

class DoNothingMiddleware:
    """Middleware that literally does nothing - just passes requests through"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        # Do absolutely nothing except pass the request through
        await self.app(scope, receive, send)

def capture_request_token(scope, receive, send):
    """
    Alternative approach: Hook into ASGI without middleware
    This function attempts to capture authentication tokens from incoming requests
    """
    async def capture_wrapper(scope, receive, send):
        # Check if this is an HTTP request
        if scope.get('type') == 'http':
            # Extract token from query string
            query_string = scope.get('query_string', b'').decode()
            if 'token=' in query_string:
                # Parse the token from query string
                import urllib.parse
                parsed = urllib.parse.parse_qs(query_string)
                if 'token' in parsed:
                    token = parsed['token'][0]
                    # Store it globally for tools to access
                    setattr(mcp, '_current_request_token', token)
                    print(f"🔑 Captured token from ASGI scope: {token[:10]}...")
            
            # Extract token from headers
            headers = dict(scope.get('headers', []))
            auth_header = headers.get(b'authorization', b'').decode()
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]  # Remove 'Bearer ' prefix
                setattr(mcp, '_current_request_token', token)
                print(f"🔑 Captured token from ASGI headers: {token[:10]}...")
        
        # Continue with normal processing
        return await send(scope, receive, send)
    
    return capture_wrapper

def get_user_from_request() -> dict:
    """
    Multi-method token extraction for true multi-user support.
    
    Token Priority:
    1. Middleware context (when CLAUDE_COMPATIBILITY=false)
    2. Proxy route intercepted token (primary method for Claude Desktop)
    3. Development environment token (for testing)
    """
    try:
        claude_compatibility = os.getenv('CLAUDE_COMPATIBILITY', 'true').lower() == 'true'
        
        if not claude_compatibility:
            # Middleware is enabled - try to get context from middleware first
            if hasattr(mcp, 'request_context') and hasattr(mcp.request_context, 'user_context'):
                user_context = mcp.request_context.user_context
                if user_context:
                    print(f"✅ Using user context from middleware for user: {user_context.get('user_id', 'unknown')}")
                    return user_context
        
        # Extract token for authentication
        token = None
        
        # Method 1: Check if FastMCP has stored the token from our /claude-mcp proxy route
        if hasattr(mcp, '_current_request_token'):
            token = mcp._current_request_token
            print(f"🔑 Using intercepted token from proxy route: {token[:10]}...")
        
        # Method 2: Check environment for development/testing
        elif os.getenv('DEV_TOKEN'):
            token = os.getenv('DEV_TOKEN')
            print(f"🔑 Using development token from environment: {token[:10]}...")
        
        # No token found
        else:
            print("❌ No authentication token found")
            return None
        
        # Look up the user by token
        from models import get_database_session, User, SpotifyToken
        from auth import decrypt_token
        
        # Get a fresh database session
        db = get_database_session()
        try:
            # Query the user directly with the session
            user = db.query(User).filter(User.api_key == token).first()
            
            if user:
                # Get the user's Spotify tokens
                spotify_token = db.query(SpotifyToken).filter(SpotifyToken.user_id == user.user_id).first()
                
                if not spotify_token:
                    print(f"❌ No Spotify tokens found for user: {user.user_id}")
                    return None
                
                # Create a simple dict with the user data we need
                user_data = {
                    "user_id": user.user_id,
                    "spotify_user_id": user.spotify_user_id,
                    "display_name": user.display_name,
                    "spotify_access_token": decrypt_token(spotify_token.access_token),
                    "spotify_refresh_token": decrypt_token(spotify_token.refresh_token) if spotify_token.refresh_token else None,
                    "token_expires_at": spotify_token.expires_at
                }
                
                print(f"✅ Authenticated user: {user.display_name} ({user.user_id})")
                return {
                    "user_id": user.user_id,
                    "user": user_data
                }
            else:
                print(f"❌ No user found for token: {token[:10]}...")
                return None
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ Error getting user from request: {e}")
        import traceback
        traceback.print_exc()
        return None

# Initialize database
print("🗄️ Initializing database...")
init_database()

# Clean up expired sessions on startup
cleanup_expired_sessions()

# Create the MCP server with environment-specific name
environment = os.getenv('ENVIRONMENT', 'dev')
transport = os.getenv('TRANSPORT', 'stdio') 
deployment = os.getenv('DEPLOYMENT', 'ngrok')

# Build server name from components
server_name = f"Spotify MCP Multi-User Server ({environment} {transport} {deployment})"
mcp = FastMCP(server_name)

# Multi-user Spotify tools with authentication
@mcp.tool
def search_tracks(query: str, limit: int = 5) -> str:
    """Search Spotify for tracks by name, artist, or keywords"""
    # Get user context from current request for multi-user support
    user_context = get_user_from_request()
    return search_tracks_impl(query, limit, user_context)

@mcp.tool
def get_current_track() -> str:
    """Get information about the currently playing track"""
    # Get user context from current request for multi-user support
    user_context = get_user_from_request()
    return get_current_track_impl(user_context)

@mcp.tool
def get_user_playlists(limit: int = 10) -> str:
    """Get the user's Spotify playlists"""
    # Get user context from current request for multi-user support
    user_context = get_user_from_request()
    return get_user_playlists_impl(limit, user_context)

@mcp.tool
def create_playlist(name: str, description: str = "", public: bool = False) -> str:
    """Create a new Spotify playlist"""
    # Get user context from current request for multi-user support
    user_context = get_user_from_request()
    return create_playlist_impl(name, description, public, user_context)

@mcp.tool
def add_tracks_to_playlist(playlist_id: str, track_uris: list) -> str:
    """Add tracks to a Spotify playlist using track URIs"""
    # Get user context from current request for multi-user support
    user_context = get_user_from_request()
    return add_tracks_to_playlist_impl(playlist_id, track_uris, user_context)

@mcp.tool
def get_liked_songs(limit: int = 20, offset: int = 0) -> str:
    """Get the user's Liked Songs (saved tracks). Use offset to paginate through results."""
    user_context = get_user_from_request()
    return get_liked_songs_impl(limit, offset, user_context)

@mcp.tool
def get_playlist_tracks(playlist_id: str, limit: int = 20, offset: int = 0) -> str:
    """Get tracks from a specific playlist. Use get_user_playlists first to find playlist IDs."""
    user_context = get_user_from_request()
    return get_playlist_tracks_impl(playlist_id, limit, offset, user_context)

@mcp.resource("spotify://status")
def get_spotify_status() -> dict:
    """Get current Spotify connection status for the authenticated user"""
    user_context = getattr(mcp.request_context, 'user_context', None)
    return get_spotify_status_impl(user_context)

@mcp.custom_route("/claude-mcp", methods=["GET", "POST", "DELETE"])
async def claude_mcp_proxy(request: Request):
    """
    Proxy route for Claude Desktop to access MCP server with user token.
    Claude Desktop will call: /claude-mcp?token=USER_TOKEN
    """
    print(f"Claude MCP proxy request: {request.method} {request.url}")
    
    # Extract token from query parameter
    token = request.query_params.get('token')
    if not token:
        return Response(content=b'{"error": "No token provided in URL parameter"}', status_code=401)
    
    # Store the token for the MCP tools to access
    mcp._current_request_token = token
    print(f"🔑 Stored token for MCP tools: {token[:10]}...")
    
    import httpx
    
    # Build the new URL for the internal /mcp endpoint
    base_url = str(request.base_url).rstrip('/')
    mcp_url = f"{base_url}/mcp"
    
    # Preserve query parameters
    if request.query_params:
        mcp_url += f"?{request.query_params}"
    
    print(f"Forwarding to: {mcp_url}")
    
    # Forward the request internally
    async with httpx.AsyncClient() as client:
        if request.method == "GET":
            response = await client.get(
                mcp_url,
                headers=dict(request.headers),
                timeout=30.0
            )
        elif request.method == "DELETE":
            response = await client.delete(
                mcp_url,
                headers=dict(request.headers),
                timeout=30.0
            )
        else:  # POST
            body = await request.body()
            response = await client.post(
                mcp_url,
                content=body,
                headers=dict(request.headers),
                timeout=30.0
            )
    
    # Return the response from /mcp
    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=dict(response.headers)
    )

@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """Health check endpoint for monitoring server status"""
    import time
    
    # Basic health info
    health_data = {
        "status": "healthy",
        "service": "Spotify MCP Multi-User Server",
        "timestamp": time.time(),
        "environment": os.getenv('ENVIRONMENT', 'dev'),
        "transport": os.getenv('TRANSPORT', 'stdio'),
        "version": "2.0.0",
        "features": [
            "multi-user",
            "token-encryption",
            "oauth-flow",
            "api-key-auth"
        ]
    }
    
    return JSONResponse(health_data)

# Add authentication routes to MCP server
# Note: FastMCP handles custom routes differently, we'll integrate them via middleware
# The auth routes will be handled by the Starlette app that FastMCP creates

def get_transport_config():
    """Determine transport configuration based on TRANSPORT variable"""
    transport = os.getenv('TRANSPORT', 'stdio').lower()
    environment = os.getenv('ENVIRONMENT', 'dev')
    
    if transport == 'http':
        # HTTP transport for web deployment or local HTTP testing
        port = int(os.getenv('PORT', 8000))
        host = os.getenv('HOST', '0.0.0.0')
        path = os.getenv('MCP_PATH', '/mcp')
        deployment = os.getenv('DEPLOYMENT', 'ngrok')
        
        print(f"🎵 Starting Spotify MCP Multi-User Server in HTTP mode")
        print(f"   Environment: {environment}")
        print(f"   Transport: HTTP")
        print(f"   Deployment: {deployment}")
        print(f"   Host: {host}")
        print(f"   Port: {port}")
        print(f"   MCP Path: {path}")
        print(f"   Auth: API key required")
        print("   Available tools: search_tracks, get_current_track, get_user_playlists, create_playlist, add_tracks_to_playlist")
        print("   Available resources: spotify://status")
        print("   Health check: /health")
        print("   Authentication: /auth/login")
        print("")
        print("🔑 To get started:")
        print(f"   1. Visit: {os.getenv('BASE_URL', f'http://localhost:{port}')}/auth/login")
        print("   2. Authenticate with Spotify")
        print("   3. Copy your API key")
        print("   4. Configure Claude Desktop with Bearer token authentication")
        print("")
        
        return {
            'transport': 'http',
            'host': host,
            'port': port,
            'path': path
        }
    else:
        # STDIO transport for local development
        deployment = os.getenv('DEPLOYMENT', 'local')
        print(f"🎵 Starting Spotify MCP Multi-User Server in STDIO mode")
        print(f"   Environment: {environment}")
        print(f"   Transport: STDIO")
        print(f"   Deployment: {deployment}")
        print("   Available tools: search_tracks, get_current_track, get_user_playlists, create_playlist, add_tracks_to_playlist")
        print("   Available resources: spotify://status")
        print("")
        print("⚠️  STDIO mode requires HTTP mode for authentication")
        print("   Run with TRANSPORT=http to enable user registration")
        print("")
        
        return {
            'transport': 'stdio'
        }

# Custom request handler to inject user context
class RequestContextHandler:
    """
    ASGI middleware for robust MCP clients that support middleware-based authentication.
    
    This middleware provides a cleaner architecture for MCP clients that can handle middleware
    without breaking tool discovery (unlike Claude Desktop which breaks with ANY middleware).
    
    Usage:
    - Enabled when CLAUDE_COMPATIBILITY=false
    - Provides more efficient authentication (once per request vs per-tool)
    - Better separation of concerns (auth logic separate from business logic)
    - Designed for VS Code extensions, CLI tools, custom MCP clients, etc.
    
    How it works:
    1. Intercepts HTTP requests to /mcp endpoints
    2. Extracts and validates authentication tokens via get_user_context()
    3. Injects user context into mcp.request_context for tools to access
    4. Tools can then use middleware-provided context instead of tool-level auth
    
    Note: Claude Desktop is incompatible with this approach and uses the /claude-mcp
    proxy route with tool-level authentication instead.
    """
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request = Request(scope, receive)
            
            # For MCP requests, get user context and inject it into FastMCP
            if request.url.path == "/mcp" or request.url.path.startswith("/mcp/"):
                user_context = get_user_context(request)
                if user_context:
                    # Store user context in FastMCP instance for tools to access
                    if not hasattr(mcp, 'request_context'):
                        mcp.request_context = type('RequestContext', (), {})()
                    mcp.request_context.user_context = user_context
                    print(f"📋 Injected user context for user: {user_context.get('user_id', 'unknown')}")
                else:
                    # Clear any existing context if authentication failed
                    if hasattr(mcp, 'request_context'):
                        mcp.request_context.user_context = None
        
        await self.app(scope, receive, send)

if __name__ == "__main__":
    # Get transport configuration based on environment
    config = get_transport_config()
    
    # Add middleware for authentication (HTTP mode only)
    if config.get('transport') == 'http':
        # Test: Add middleware that does absolutely nothing to see if ANY middleware breaks Claude Desktop
        print("🧪 Testing with do-nothing middleware to isolate Claude Desktop compatibility issue")
        # mcp.add_middleware(DoNothingMiddleware)  # DISABLED - STILL BREAKS IN FASTMCP 2.12.4
        
        # Check if we should enable full middleware based on client detection
        claude_compatibility = os.getenv('CLAUDE_COMPATIBILITY', 'true').lower() == 'true'
        
        if claude_compatibility:
            # Disable additional middleware for Claude Desktop compatibility - use tool-level auth instead
            print("🔧 Additional middleware disabled for Claude Desktop compatibility - using tool-level authentication")
            print("   Set CLAUDE_COMPATIBILITY=false to enable full middleware for other MCP clients")
            
            # NO MIDDLEWARE for Claude Desktop - it breaks tool discovery
        else:
            # Enable full middleware for non-Claude MCP clients (VS Code extensions, CLI tools, etc.)
            print("🔧 Enabling full authentication middleware for non-Claude MCP clients")
            print("   Note: This may not work with Claude Desktop - set CLAUDE_COMPATIBILITY=true if needed")
            
            # Add session middleware first
            from starlette.middleware.sessions import SessionMiddleware
            session_middleware = lambda app: SessionMiddleware(app, secret_key=os.getenv('SESSION_SECRET_KEY', 'dev-secret-key'))
            mcp.add_middleware(session_middleware)
            
            # Add our authentication middleware
            mcp.add_middleware(MCPAuthMiddleware)
            
            # Add request context handler to inject user context
            mcp.add_middleware(RequestContextHandler)
        
        # Add authentication routes using custom route decorator
        from starlette.routing import Route
        from starlette.applications import Starlette
        
        @mcp.custom_route("/auth/login", methods=["GET"])
        async def auth_login_route(request):
            from web_auth import auth_login
            return await auth_login(request)
        
        @mcp.custom_route("/auth/callback", methods=["GET"])
        async def auth_callback_route(request):
            from web_auth import auth_callback
            return await auth_callback(request)
            
        @mcp.custom_route("/auth/status", methods=["GET"])
        async def auth_status_route(request):
            from web_auth import auth_status
            return await auth_status(request)
            
        @mcp.custom_route("/auth/revoke", methods=["POST", "DELETE"])
        async def auth_revoke_route(request):
            from web_auth import auth_revoke
            return await auth_revoke(request)
    
    # Start the MCP server with appropriate transport
    mcp.run(**config)
