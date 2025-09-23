#!/usr/bin/env python3
"""
Hosted Spotify MCP Server for Cloudflare Workers
Multi-user version with HTTP transport
"""

import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from fastmcp import FastMCP
from dotenv import load_dotenv

load_dotenv()

# Create MCP server for HTTP transport
mcp = FastMCP("HostedSpotifyServer")

def get_spotify_client():
    """Get authenticated Spotify client - will need multi-user support later"""
    auth_manager = SpotifyOAuth(
        client_id=os.getenv('SPOTIFY_CLIENT_ID'),
        client_secret=os.getenv('SPOTIFY_CLIENT_SECRET'),
        redirect_uri=os.getenv('SPOTIFY_REDIRECT_URI'),
        scope='user-library-read playlist-read-private user-read-playback-state playlist-modify-public playlist-modify-private'
    )
    return spotipy.Spotify(auth_manager=auth_manager)

# Same tools as your local version
@mcp.tool
def search_tracks(query: str, limit: int = 5) -> str:
    """Search Spotify for tracks by name, artist, or keywords"""
    try:
        sp = get_spotify_client()
        results = sp.search(q=query, type='track', limit=limit)
        
        if not results['tracks']['items']:
            return f"No tracks found for '{query}'"
        
        tracks = []
        for track in results['tracks']['items']:
            artists = ', '.join([artist['name'] for artist in track['artists']])
            tracks.append(f"🎵 {track['name']} by {artists} (URI: {track['uri']})")
        
        return f"Found {len(tracks)} tracks for '{query}':\n" + "\n".join(tracks)
    
    except Exception as e:
        return f"Error searching tracks: {str(e)}"

@mcp.tool 
def get_current_track() -> str:
    """Get information about the currently playing track"""
    try:
        sp = get_spotify_client()
        current = sp.current_playback()
        
        if not current or not current['is_playing']:
            return "No track currently playing"
        
        track = current['item']
        artists = ', '.join([artist['name'] for artist in track['artists']])
        progress = current['progress_ms'] // 1000
        duration = track['duration_ms'] // 1000
        
        return f"🎵 Currently playing: {track['name']} by {artists}\n⏱️ Progress: {progress//60}:{progress%60:02d} / {duration//60}:{duration%60:02d}\n🔗 URI: {track['uri']}"
    
    except Exception as e:
        return f"Error getting current track: {str(e)}"

@mcp.tool
def get_user_playlists(limit: int = 10) -> str:
    """Get the user's Spotify playlists"""
    try:
        sp = get_spotify_client()
        playlists = sp.current_user_playlists(limit=limit)
        
        if not playlists['items']:
            return "No playlists found"
        
        playlist_list = []
        for playlist in playlists['items']:
            playlist_list.append(f"📋 {playlist['name']} ({playlist['tracks']['total']} tracks) - ID: {playlist['id']}")
        
        return f"Your playlists:\n" + "\n".join(playlist_list)
    
    except Exception as e:
        return f"Error getting playlists: {str(e)}"

@mcp.tool
def create_playlist(name: str, description: str = "", public: bool = False) -> str:
    """Create a new Spotify playlist"""
    try:
        sp = get_spotify_client()
        user = sp.current_user()
        
        playlist = sp.user_playlist_create(
            user=user['id'],
            name=name,
            public=public,
            description=description
        )
        
        return f"✅ Created playlist '{name}' (ID: {playlist['id']})\n🔗 {playlist['external_urls']['spotify']}"
    
    except Exception as e:
        return f"Error creating playlist: {str(e)}"

@mcp.tool
def add_tracks_to_playlist(playlist_id: str, track_uris: list) -> str:
    """Add tracks to a Spotify playlist using track URIs"""
    try:
        sp = get_spotify_client()
        sp.playlist_add_items(playlist_id, track_uris)
        return f"✅ Added {len(track_uris)} tracks to playlist"
    
    except Exception as e:
        return f"Error adding tracks to playlist: {str(e)}"

@mcp.resource("spotify://status")
def get_spotify_status() -> dict:
    """Get current Spotify connection status"""
    try:
        sp = get_spotify_client()
        user = sp.current_user()
        return {
            "connected": True,
            "user": user['display_name'],
            "user_id": user['id'],
            "server": "HostedSpotifyServer",
            "version": "1.0.0"
        }
    except Exception as e:
        return {
            "connected": False,
            "error": str(e),
            "server": "HostedSpotifyServer",
            "version": "1.0.0"
        }

# HTTP server instead of stdio
# HTTP server instead of stdio
if __name__ == "__main__":
    print("🎵 Starting Hosted Spotify MCP Server...")
    print("Available tools: search_tracks, get_current_track, get_user_playlists, create_playlist, add_tracks_to_playlist")
    print("Available resources: spotify://status")
    
    # Run as HTTP server - try different FastMCP methods
    try:
        # Method 1: Try direct HTTP run
        mcp.run(transport="sse", host="0.0.0.0", port=8000)
    except Exception as e:
        print(f"Method 1 failed: {e}")
        try:
            # Method 2: Try with different syntax
            mcp.run_sse(host="0.0.0.0", port=8000)
        except Exception as e:
            print(f"Method 2 failed: {e}")
            # Method 3: Fall back to stdio for now
            print("Falling back to stdio transport for testing...")
            mcp.run()