#!/usr/bin/env python3
"""
Spotify client utilities for multi-user support
Handles OAuth flow and creates user-specific clients
"""

import os
import spotipy
from datetime import datetime, timezone, timedelta
from spotipy.oauth2 import SpotifyOAuth
from typing import Optional, Dict, Any
from auth import get_user_tokens, tokens_need_refresh, update_user_tokens

class SpotifyClientManager:
    """Manages Spotify clients for multiple users"""
    
    def __init__(self):
        self.client_id = os.getenv('SPOTIFY_CLIENT_ID')
        self.client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
        self.redirect_uri = os.getenv('SPOTIFY_REDIRECT_URI', 'http://localhost:8001/auth/callback')
        self.scope = 'user-library-read playlist-read-private user-read-playback-state playlist-modify-public playlist-modify-private user-read-currently-playing'
        
        # Don't raise error immediately - allow for testing without credentials
        self._credentials_valid = bool(self.client_id and self.client_secret)
        if not self._credentials_valid:
            print("⚠️  SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET not set - Spotify functionality will be limited")
    
    def _check_credentials(self):
        """Check if credentials are available and raise error if not"""
        if not self._credentials_valid:
            raise ValueError("SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set")
    
    def get_auth_manager(self, state: str = None) -> SpotifyOAuth:
        """Get Spotify OAuth manager with NO caching"""
        self._check_credentials()
        return SpotifyOAuth(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
            scope=self.scope,
            state=state,
            cache_handler=None  # Disable caching completely
        )
    
    def get_authorization_url(self, state: str) -> str:
        """Get Spotify authorization URL"""
        auth_manager = self.get_auth_manager(state)
        return auth_manager.get_authorize_url()
    
    def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens"""
        auth_manager = self.get_auth_manager()
        token_info = auth_manager.get_access_token(code)
        return token_info
    
    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using refresh token"""
        auth_manager = self.get_auth_manager()
        token_info = auth_manager.refresh_access_token(refresh_token)
        return token_info
        return token_info
    
    def get_user_spotify_client(self, user_id: str) -> Optional[spotipy.Spotify]:
        """Get authenticated Spotify client for a specific user"""
        try:
            # Get user tokens
            token_data = get_user_tokens(user_id)
            if not token_data:
                print(f"No tokens found for user {user_id}")
                return None
            
            access_token, refresh_token, expires_at = token_data
            
            # Check if tokens need refresh
            if tokens_need_refresh(expires_at):
                print(f"Refreshing tokens for user {user_id}")
                try:
                    new_token_info = self.refresh_access_token(refresh_token)
                    
                    # Update stored tokens
                    new_expires_at = datetime.now(timezone.utc) + timedelta(seconds=new_token_info['expires_in'])
                    update_user_tokens(
                        user_id,
                        new_token_info['access_token'],
                        new_token_info.get('refresh_token', refresh_token),  # Sometimes refresh token doesn't change
                        new_expires_at
                    )
                    
                    access_token = new_token_info['access_token']
                    print(f"✅ Refreshed tokens for user {user_id}")
                    
                except Exception as e:
                    print(f"Error refreshing tokens for user {user_id}: {e}")
                    return None
            
            # Create Spotify client
            return spotipy.Spotify(auth=access_token)
            
        except Exception as e:
            print(f"Error getting Spotify client for user {user_id}: {e}")
            return None
    
    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile from Spotify"""
        client = self.get_user_spotify_client(user_id)
        if not client:
            return None
        
        try:
            return client.current_user()
        except Exception as e:
            print(f"Error getting user profile for {user_id}: {e}")
            return None
    
    def test_user_connection(self, user_id: str) -> bool:
        """Test if user's Spotify connection is working"""
        client = self.get_user_spotify_client(user_id)
        if not client:
            return False
        
        try:
            client.current_user()
            return True
        except Exception as e:
            print(f"Connection test failed for user {user_id}: {e}")
            return False

# Global instance
spotify_manager = SpotifyClientManager()
