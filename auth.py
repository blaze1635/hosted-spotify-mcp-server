#!/usr/bin/env python3
"""
Authentication utilities for Spotify MCP Server
API key generation, validation, and user management
"""

import os
import secrets
import string
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
from models import User, SpotifyToken, UserSession, get_database_session, encrypt_token, decrypt_token

def generate_api_key(length: int = 32) -> str:
    """Generate a secure API key"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_user_id() -> str:
    """Generate a unique user ID"""
    import uuid
    return str(uuid.uuid4())

def create_user(spotify_user_id: str, display_name: str = None, email: str = None) -> Tuple[User, str]:
    """Create a new user and return the user object and API key"""
    db = get_database_session()
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.spotify_user_id == spotify_user_id).first()
        if existing_user:
            # Return existing user and their API key
            return existing_user, existing_user.api_key
        
        # Create new user
        api_key = generate_api_key()
        user = User(
            user_id=generate_user_id(),
            api_key=api_key,
            spotify_user_id=spotify_user_id,
            display_name=display_name,
            email=email
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        print(f"✅ Created new user: {display_name} ({spotify_user_id})")
        return user, api_key
        
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

def store_spotify_tokens(user_id: str, access_token: str, refresh_token: str, expires_at: datetime, scope: str = None):
    """Store or update Spotify tokens for a user"""
    db = get_database_session()
    try:
        # Encrypt tokens
        encrypted_access = encrypt_token(access_token)
        encrypted_refresh = encrypt_token(refresh_token)
        
        # Check if tokens already exist
        existing_tokens = db.query(SpotifyToken).filter(SpotifyToken.user_id == user_id).first()
        
        if existing_tokens:
            # Update existing tokens
            existing_tokens.access_token = encrypted_access
            existing_tokens.refresh_token = encrypted_refresh
            existing_tokens.expires_at = expires_at
            existing_tokens.scope = scope
            existing_tokens.updated_at = datetime.now(timezone.utc)
        else:
            # Create new token record
            tokens = SpotifyToken(
                user_id=user_id,
                access_token=encrypted_access,
                refresh_token=encrypted_refresh,
                expires_at=expires_at,
                scope=scope
            )
            db.add(tokens)
        
        db.commit()
        print(f"✅ Stored tokens for user {user_id}")
        
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

def get_user_by_api_key(api_key: str) -> Optional[User]:
    """Get user by API key"""
    db = get_database_session()
    try:
        user = db.query(User).filter(User.api_key == api_key).first()
        if user:
            # Update last active time
            user.last_active = datetime.now(timezone.utc)
            db.commit()
        return user
    except Exception as e:
        print(f"Error getting user by API key: {e}")
        return None
    finally:
        db.close()

def get_user_tokens(user_id: str) -> Optional[Tuple[str, str, datetime]]:
    """Get decrypted tokens for a user"""
    db = get_database_session()
    try:
        tokens = db.query(SpotifyToken).filter(SpotifyToken.user_id == user_id).first()
        if not tokens:
            return None
        
        # Decrypt tokens
        access_token = decrypt_token(tokens.access_token)
        refresh_token = decrypt_token(tokens.refresh_token)
        
        return access_token, refresh_token, tokens.expires_at
        
    except Exception as e:
        print(f"Error getting user tokens: {e}")
        return None
    finally:
        db.close()

def validate_api_key(api_key: str) -> Optional[str]:
    """Validate API key and return user_id if valid"""
    user = get_user_by_api_key(api_key)
    return user.user_id if user else None

def tokens_need_refresh(expires_at: datetime) -> bool:
    """Check if tokens need to be refreshed (5 minute buffer)"""
    buffer_time = datetime.now(timezone.utc) + timedelta(minutes=5)
    
    # Ensure expires_at is timezone-aware for comparison
    if expires_at.tzinfo is None:
        # If naive, assume UTC
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    
    return expires_at <= buffer_time

def update_user_tokens(user_id: str, access_token: str, refresh_token: str, expires_at: datetime):
    """Update user tokens after refresh"""
    store_spotify_tokens(user_id, access_token, refresh_token, expires_at)

def create_user_session(user_id: str, api_key: str, session_id: str = None) -> UserSession:
    """Create a user session for MCP connection"""
    if not session_id:
        session_id = generate_api_key(16)
    
    db = get_database_session()
    try:
        # Remove any existing session for this user
        db.query(UserSession).filter(UserSession.user_id == user_id).delete()
        
        # Create new session
        session = UserSession(
            session_id=session_id,
            user_id=user_id,
            api_key=api_key,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30)  # 30 day session
        )
        
        db.add(session)
        db.commit()
        db.refresh(session)
        
        return session
        
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

def get_session_by_api_key(api_key: str) -> Optional[UserSession]:
    """Get active session by API key"""
    db = get_database_session()
    try:
        session = db.query(UserSession).filter(
            UserSession.api_key == api_key,
            UserSession.expires_at > datetime.now(timezone.utc)
        ).first()
        
        if session:
            # Update last activity
            session.last_activity = datetime.now(timezone.utc)
            db.commit()
        
        return session
        
    except Exception as e:
        print(f"Error getting session by API key: {e}")
        return None
    finally:
        db.close()

def cleanup_expired_sessions():
    """Clean up expired sessions"""
    db = get_database_session()
    try:
        expired_count = db.query(UserSession).filter(
            UserSession.expires_at <= datetime.now(timezone.utc)
        ).delete()
        
        db.commit()
        if expired_count > 0:
            print(f"🧹 Cleaned up {expired_count} expired sessions")
        
    except Exception as e:
        print(f"Error cleaning up sessions: {e}")
    finally:
        db.close()
