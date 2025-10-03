#!/usr/bin/env python3
"""
Web authentication routes for Spotify MCP Server
OAuth flow, user registration, and API key management
"""

import os
import json
import secrets
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse
from starlette.routing import Route
from auth import create_user, store_spotify_tokens, get_user_by_api_key, create_user_session
from spotify_client import spotify_manager

def generate_state() -> str:
    """Generate secure state parameter for OAuth"""
    return secrets.token_urlsafe(32)

async def auth_login(request: Request) -> HTMLResponse:
    """Initiate Spotify OAuth flow"""
    try:
        # Generate secure state
        state = generate_state()
        
        # Get authorization URL
        auth_url = spotify_manager.get_authorization_url(state)
        
        # Store state in session if available, otherwise skip session validation
        # This is a temporary fix - in production you'd want proper session management
        try:
            if hasattr(request, 'session'):
                request.session['oauth_state'] = state
        except Exception as e:
            print(f"Warning: Could not store state in session: {e}")
            # Continue without session - less secure but allows testing
        
        # Return HTML page that redirects to Spotify
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Spotify MCP Server - Login</title>
            <style>
                body {{ 
                    font-family: Arial, sans-serif; 
                    max-width: 600px; 
                    margin: 50px auto; 
                    padding: 20px;
                    background: linear-gradient(135deg, #1DB954, #191414);
                    color: white;
                    text-align: center;
                }}
                .container {{ 
                    background: rgba(0,0,0,0.8); 
                    padding: 40px; 
                    border-radius: 10px; 
                }}
                .logo {{ font-size: 48px; margin-bottom: 20px; }}
                .button {{ 
                    background: #1DB954; 
                    color: white; 
                    padding: 15px 30px; 
                    text-decoration: none; 
                    border-radius: 25px; 
                    display: inline-block; 
                    margin: 20px 0;
                    font-size: 18px;
                    font-weight: bold;
                }}
                .button:hover {{ background: #1ed760; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="logo">🎵</div>
                <h1>Spotify MCP Server</h1>
                <p>Welcome! To use this server with Claude Desktop, you need to connect your Spotify account.</p>
                <p>Click the button below to authorize this application to access your Spotify account.</p>
                <a href="{auth_url}" class="button">Connect to Spotify</a>
                <p><small>You'll be redirected to Spotify to grant permissions, then back here to get your API key.</small></p>
            </div>
        </body>
        </html>
        """
        
        return HTMLResponse(html_content)
        
    except Exception as e:
        return HTMLResponse(f"""
        <html><body>
            <h1>Error</h1>
            <p>Failed to initiate Spotify login: {str(e)}</p>
        </body></html>
        """, status_code=500)

async def auth_callback(request: Request) -> HTMLResponse:
    """Handle Spotify OAuth callback"""
    try:
        # Get authorization code and state from callback
        query_params = request.query_params
        code = query_params.get('code')
        state = query_params.get('state')
        error = query_params.get('error')
        
        if error:
            return HTMLResponse(f"""
            <html><body>
                <h1>Authorization Denied</h1>
                <p>Spotify authorization was denied: {error}</p>
                <p><a href="/auth/login">Try again</a></p>
            </body></html>
            """, status_code=400)
        
        if not code:
            return HTMLResponse("""
            <html><body>
                <h1>Missing Authorization Code</h1>
                <p>No authorization code received from Spotify.</p>
                <p><a href="/auth/login">Try again</a></p>
            </body></html>
            """, status_code=400)
        
        # Exchange code for tokens
        token_info = spotify_manager.exchange_code_for_tokens(code)
        print(f"🔑 Token info received: access_token={token_info['access_token'][:20]}...")
        
        # Get user profile using the fresh access token
        import spotipy
        sp = spotipy.Spotify(auth=token_info['access_token'])
        user_profile = sp.current_user()
        
        # Debug: Log the Spotify user info
        print(f"🔍 Spotify user profile: {user_profile['id']} ({user_profile.get('display_name', 'No name')})")
        print(f"🔍 Spotify user email: {user_profile.get('email', 'No email')}")
        print(f"🔍 Full profile: {user_profile}")
        
        # Create or get existing user
        user, api_key = create_user(
            spotify_user_id=user_profile['id'],
            display_name=user_profile.get('display_name', ''),
            email=user_profile.get('email', '')
        )
        
        # Store tokens
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=token_info['expires_in'])
        store_spotify_tokens(
            user_id=user.user_id,
            access_token=token_info['access_token'],
            refresh_token=token_info['refresh_token'],
            expires_at=expires_at,
            scope=token_info.get('scope', '')
        )
        
        # Create user session
        create_user_session(user.user_id, api_key)
        
        # Return success page with API key
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Spotify MCP Server - Success</title>
            <style>
                body {{ 
                    font-family: Arial, sans-serif; 
                    max-width: 700px; 
                    margin: 50px auto; 
                    padding: 20px;
                    background: linear-gradient(135deg, #1DB954, #191414);
                    color: white;
                }}
                .container {{ 
                    background: rgba(0,0,0,0.8); 
                    padding: 40px; 
                    border-radius: 10px; 
                }}
                .success {{ color: #1DB954; font-size: 48px; text-align: center; }}
                .api-key {{ 
                    background: #333; 
                    padding: 15px; 
                    border-radius: 5px; 
                    font-family: monospace; 
                    word-break: break-all;
                    border: 2px solid #1DB954;
                }}
                .copy-btn {{ 
                    background: #1DB954; 
                    color: white; 
                    padding: 10px 20px; 
                    border: none; 
                    border-radius: 5px; 
                    cursor: pointer; 
                    margin: 10px 0;
                }}
                .instructions {{ 
                    background: #2a2a2a; 
                    padding: 20px; 
                    border-radius: 5px; 
                    margin: 20px 0; 
                }}
            </style>
            <script>
                function copyApiKey() {{
                    navigator.clipboard.writeText('{api_key}');
                    alert('API key copied to clipboard!');
                }}
            </script>
        </head>
        <body>
            <div class="container">
                <div class="success">✅</div>
                <h1>Successfully Connected!</h1>
                <p>Welcome, <strong>{user_profile.get('display_name', user_profile['id'])}!</strong></p>
                <p>Your Spotify account has been connected to the MCP server.</p>
                
                <h3>Your API Key:</h3>
                <div class="api-key">{api_key}</div>
                <button class="copy-btn" onclick="copyApiKey()">Copy API Key</button>
                
                <div class="instructions">
                    <h3>Next Steps - Configure Claude Desktop:</h3>
                    <ol>
                        <li>Open Claude Desktop settings</li>
                        <li>Add a new MCP server with these settings:
                            <ul>
                                <li><strong>Name:</strong> Spotify</li>
                                <li><strong>URL:</strong> {os.getenv('BASE_URL', 'https://6ecabf48ee60.ngrok-free.app')}/claude-mcp?token={api_key}</li>
                                <li><strong>Authentication:</strong> None (token included in URL)</li>
                            </ul>
                        </li>
                        <li>Save and restart Claude Desktop</li>
                        <li>Test by asking: "Search for my favorite music on Spotify"</li>
                    </ol>
                </div>
                
                <div class="instructions">
                    <h3>Available Commands:</h3>
                    <ul>
                        <li>Search for songs: "Search for Taylor Swift songs"</li>
                        <li>Current track: "What's currently playing on Spotify?"</li>
                        <li>Your playlists: "Show my Spotify playlists"</li>
                        <li>Create playlist: "Create a new playlist called 'Road Trip'"</li>
                        <li>Add songs: "Add these songs to my playlist"</li>
                    </ul>
                </div>
                
                <p><small>Keep your API key secure! You can revoke access anytime through your Spotify account settings.</small></p>
            </div>
        </body>
        </html>
        """
        
        return HTMLResponse(html_content)
        
    except Exception as e:
        return HTMLResponse(f"""
        <html><body style="font-family: Arial; padding: 50px;">
            <h1>Error</h1>
            <p>Failed to complete Spotify authentication: {str(e)}</p>
            <p><a href="/auth/login">Try again</a></p>
        </body></html>
        """, status_code=500)

async def auth_status(request: Request) -> JSONResponse:
    """Check authentication status for an API key"""
    try:
        # Get API key from Authorization header
        auth_header = request.headers.get('authorization', '')
        if not auth_header.startswith('Bearer '):
            return JSONResponse({"error": "Missing or invalid authorization header"}, status_code=401)
        
        api_key = auth_header[7:]  # Remove "Bearer "
        user = get_user_by_api_key(api_key)
        
        if not user:
            return JSONResponse({"error": "Invalid API key"}, status_code=401)
        
        # Test Spotify connection
        connection_ok = spotify_manager.test_user_connection(user.user_id)
        
        return JSONResponse({
            "authenticated": True,
            "user_id": user.user_id,
            "display_name": user.display_name,
            "spotify_user_id": user.spotify_user_id,
            "spotify_connected": connection_ok,
            "last_active": user.last_active.isoformat(),
            "created_at": user.created_at.isoformat()
        })
        
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

async def auth_revoke(request: Request) -> JSONResponse:
    """Revoke user access (delete tokens)"""
    try:
        # Get API key from Authorization header
        auth_header = request.headers.get('authorization', '')
        if not auth_header.startswith('Bearer '):
            return JSONResponse({"error": "Missing or invalid authorization header"}, status_code=401)
        
        api_key = auth_header[7:]
        user = get_user_by_api_key(api_key)
        
        if not user:
            return JSONResponse({"error": "Invalid API key"}, status_code=401)
        
        # Delete user and all associated data
        from models import get_database_session
        db = get_database_session()
        try:
            # This will cascade delete tokens and sessions
            db.delete(user)
            db.commit()
            
            return JSONResponse({
                "message": "Access revoked successfully",
                "user_id": user.user_id
            })
            
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
            
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# Define routes
auth_routes = [
    Route("/auth/login", auth_login, methods=["GET"]),
    Route("/auth/callback", auth_callback, methods=["GET"]),
    Route("/auth/status", auth_status, methods=["GET"]),
    Route("/auth/revoke", auth_revoke, methods=["POST", "DELETE"]),
]
