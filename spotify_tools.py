#!/usr/bin/env python3
"""
Multi-user Spotify tools for MCP Server
All tools now support multiple users via API key authentication
"""

from typing import Optional, Dict, Any
from spotify_client import spotify_manager

def get_user_spotify_client_for_tool(user_context: Dict[str, Any]):
    """Get Spotify client for the authenticated user"""
    if not user_context or 'user_id' not in user_context:
        raise ValueError("No user context provided")
    
    client = spotify_manager.get_user_spotify_client(user_context['user_id'])
    if not client:
        raise ValueError("Failed to get Spotify client. Please re-authenticate at /auth/login")
    
    return client

def search_tracks_impl(query: str, limit: int = 5, user_context: Dict[str, Any] = None) -> str:
    """Search Spotify for tracks by name, artist, or keywords"""
    try:
        sp = get_user_spotify_client_for_tool(user_context)
        results = sp.search(q=query, type='track', limit=limit)
        
        if not results['tracks']['items']:
            return f"No tracks found for '{query}'"
        
        tracks = []
        for track in results['tracks']['items']:
            artists = ', '.join([artist['name'] for artist in track['artists']])
            tracks.append(f"🎵 {track['name']} by {artists} (URI: {track['uri']})")
        
        user_name = user_context.get('user', {}).get('display_name', 'User')
        return f"Found {len(tracks)} tracks for '{query}' (searched by {user_name}):\n" + "\n".join(tracks)
    
    except Exception as e:
        return f"Error searching tracks: {str(e)}"

def get_current_track_impl(user_context: Dict[str, Any] = None) -> str:
    """Get information about the currently playing track"""
    try:
        sp = get_user_spotify_client_for_tool(user_context)
        current = sp.current_playback()
        
        if not current or not current['is_playing']:
            user_name = user_context.get('user', {}).get('display_name', 'User')
            return f"No track currently playing for {user_name}"
        
        track = current['item']
        if not track:
            return "No track information available"
        
        artists = ', '.join([artist['name'] for artist in track['artists']])
        progress = current['progress_ms'] // 1000
        duration = track['duration_ms'] // 1000
        device = current.get('device', {}).get('name', 'Unknown device')
        
        user_name = user_context.get('user', {}).get('display_name', 'User')
        
        return (f"🎵 Currently playing for {user_name}:\n"
                f"   {track['name']} by {artists}\n"
                f"⏱️ Progress: {progress//60}:{progress%60:02d} / {duration//60}:{duration%60:02d}\n"
                f"📱 Device: {device}\n"
                f"🔗 URI: {track['uri']}")
    
    except Exception as e:
        return f"Error getting current track: {str(e)}"

def get_user_playlists_impl(limit: int = 10, user_context: Dict[str, Any] = None) -> str:
    """Get the user's Spotify playlists"""
    try:
        sp = get_user_spotify_client_for_tool(user_context)
        playlists = sp.current_user_playlists(limit=limit)
        
        if not playlists['items']:
            user_name = user_context.get('user', {}).get('display_name', 'User')
            return f"No playlists found for {user_name}"
        
        playlist_list = []
        for playlist in playlists['items']:
            owner = playlist['owner']['display_name']
            playlist_list.append(f"📋 {playlist['name']} by {owner} ({playlist['tracks']['total']} tracks) - ID: {playlist['id']}")
        
        user_name = user_context.get('user', {}).get('display_name', 'User')
        return f"Playlists for {user_name}:\n" + "\n".join(playlist_list)
    
    except Exception as e:
        return f"Error getting playlists: {str(e)}"

def create_playlist_impl(name: str, description: str = "", public: bool = False, user_context: Dict[str, Any] = None) -> str:
    """Create a new Spotify playlist"""
    try:
        sp = get_user_spotify_client_for_tool(user_context)
        user_profile = sp.current_user()
        
        playlist = sp.user_playlist_create(
            user=user_profile['id'],
            name=name,
            public=public,
            description=description
        )
        
        user_name = user_context.get('user', {}).get('display_name', 'User')
        
        return (f"✅ Created playlist '{name}' for {user_name}\n"
                f"📋 ID: {playlist['id']}\n"
                f"🔗 {playlist['external_urls']['spotify']}")
    
    except Exception as e:
        return f"Error creating playlist: {str(e)}"

def add_tracks_to_playlist_impl(playlist_id: str, track_uris: list, user_context: Dict[str, Any] = None) -> str:
    """Add tracks to a Spotify playlist using track URIs"""
    try:
        sp = get_user_spotify_client_for_tool(user_context)
        
        # Validate track URIs
        valid_uris = []
        for uri in track_uris:
            if uri.startswith('spotify:track:'):
                valid_uris.append(uri)
            else:
                # Try to convert if it's just an ID
                if len(uri) == 22 and uri.isalnum():
                    valid_uris.append(f'spotify:track:{uri}')
                else:
                    return f"Invalid track URI format: {uri}"
        
        sp.playlist_add_items(playlist_id, valid_uris)
        user_name = user_context.get('user', {}).get('display_name', 'User')
        
        return f"✅ Added {len(valid_uris)} tracks to playlist for {user_name}"
    
    except Exception as e:
        return f"Error adding tracks to playlist: {str(e)}"

def get_liked_songs_impl(limit: int = 20, offset: int = 0, user_context: Dict[str, Any] = None) -> str:
    """Get the user's Liked Songs (saved tracks)"""
    try:
        sp = get_user_spotify_client_for_tool(user_context)
        results = sp.current_user_saved_tracks(limit=limit, offset=offset)

        if not results['items']:
            user_name = user_context.get('user', {}).get('display_name', 'User')
            return f"No liked songs found for {user_name}"

        tracks = []
        for item in results['items']:
            track = item['track']
            artists = ', '.join([artist['name'] for artist in track['artists']])
            added_at = item.get('added_at', '')[:10]  # Just the date
            tracks.append(f"🎵 {track['name']} by {artists} (added {added_at}) (URI: {track['uri']})")

        total = results['total']
        user_name = user_context.get('user', {}).get('display_name', 'User')
        header = f"Liked Songs for {user_name} (showing {offset+1}-{offset+len(tracks)} of {total}):\n"
        return header + "\n".join(tracks)

    except Exception as e:
        return f"Error getting liked songs: {str(e)}"

def get_playlist_tracks_impl(playlist_id: str, limit: int = 20, offset: int = 0, user_context: Dict[str, Any] = None) -> str:
    """Get tracks from a specific playlist"""
    try:
        sp = get_user_spotify_client_for_tool(user_context)
        results = sp.playlist_tracks(playlist_id, limit=limit, offset=offset)

        if not results['items']:
            return f"No tracks found in playlist {playlist_id}"

        tracks = []
        for item in results['items']:
            track = item.get('track')
            if not track:
                continue
            artists = ', '.join([artist['name'] for artist in track['artists']])
            added_at = item.get('added_at', '')[:10]
            tracks.append(f"🎵 {track['name']} by {artists} (added {added_at}) (URI: {track['uri']})")

        total = results['total']
        user_name = user_context.get('user', {}).get('display_name', 'User')
        header = f"Playlist tracks for {user_name} (showing {offset+1}-{offset+len(tracks)} of {total}):\n"
        return header + "\n".join(tracks)

    except Exception as e:
        return f"Error getting playlist tracks: {str(e)}"

def get_spotify_status_impl(user_context: Dict[str, Any] = None) -> dict:
    """Get current Spotify connection status for the user"""
    try:
        if not user_context:
            return {
                "connected": False,
                "error": "No user context provided"
            }
        
        user = user_context.get('user')
        sp = get_user_spotify_client_for_tool(user_context)
        spotify_profile = sp.current_user()
        
        return {
            "connected": True,
            "user": user.display_name if user else "Unknown",
            "user_id": user.user_id if user else "Unknown", 
            "spotify_user": spotify_profile['display_name'],
            "spotify_user_id": spotify_profile['id'],
            "server": "Spotify MCP Server Multi-User",
            "version": "2.0.0"
        }
    except Exception as e:
        return {
            "connected": False,
            "error": str(e),
            "server": "Spotify MCP Server Multi-User",
            "version": "2.0.0"
        }
