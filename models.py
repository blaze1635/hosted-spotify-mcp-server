#!/usr/bin/env python3
"""
Database models for Spotify MCP Server
Multi-user authentication and token storage
"""

import os
import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import create_engine, Column, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from cryptography.fernet import Fernet

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./spotify_users.db")

# Handle PostgreSQL URL format for SQLAlchemy
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Encryption setup
ENCRYPTION_KEY = os.getenv("TOKEN_ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    # Generate a key for development - in production, this should be set as env var
    ENCRYPTION_KEY = Fernet.generate_key().decode()
    print(f"⚠️  Generated encryption key for development: {ENCRYPTION_KEY}")
    print("   Set TOKEN_ENCRYPTION_KEY environment variable in production")

# Ensure the key is in the correct format
try:
    if isinstance(ENCRYPTION_KEY, str):
        # Try to decode to validate it's a proper base64 Fernet key
        test_cipher = Fernet(ENCRYPTION_KEY.encode())
        cipher_suite = test_cipher
    else:
        cipher_suite = Fernet(ENCRYPTION_KEY)
except (ValueError, TypeError):
    # Invalid key format, generate a new one
    ENCRYPTION_KEY = Fernet.generate_key().decode()
    print(f"⚠️  Invalid encryption key format, generated new key: {ENCRYPTION_KEY}")
    print("   Update TOKEN_ENCRYPTION_KEY environment variable")
    cipher_suite = Fernet(ENCRYPTION_KEY.encode())

class User(Base):
    """User model for storing user information"""
    __tablename__ = "users"
    
    user_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    api_key = Column(String, unique=True, nullable=False)
    spotify_user_id = Column(String, unique=True, nullable=False)
    display_name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_active = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationship to tokens
    tokens = relationship("SpotifyToken", back_populates="user", cascade="all, delete-orphan")

class SpotifyToken(Base):
    """Spotify token storage with encryption"""
    __tablename__ = "spotify_tokens"
    
    user_id = Column(String, ForeignKey("users.user_id"), primary_key=True)
    access_token = Column(Text, nullable=False)  # Encrypted
    refresh_token = Column(Text, nullable=False)  # Encrypted
    expires_at = Column(DateTime, nullable=False)
    scope = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationship to user
    user = relationship("User", back_populates="tokens")

class UserSession(Base):
    """Active user sessions for MCP connections"""
    __tablename__ = "user_sessions"
    
    session_id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)
    api_key = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_activity = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=True)
    
    # Relationship to user
    user = relationship("User")

def encrypt_token(token: str) -> str:
    """Encrypt a token for storage"""
    return cipher_suite.encrypt(token.encode()).decode()

def decrypt_token(encrypted_token: str) -> str:
    """Decrypt a token from storage"""
    return cipher_suite.decrypt(encrypted_token.encode()).decode()

def get_database_session():
    """Get a database session"""
    return SessionLocal()

def init_database():
    """Initialize the database tables"""
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables initialized")

if __name__ == "__main__":
    init_database()
