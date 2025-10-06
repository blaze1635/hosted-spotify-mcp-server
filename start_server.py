#!/usr/bin/env python3
"""
Startup script for Spotify MCP Multi-User Server
Handles initialization and provides helpful startup information
"""

import os
import sys
from pathlib import Path

def check_environment():
    """Check if environment is properly configured"""
    required_vars = [
        'SPOTIFY_CLIENT_ID',
        'SPOTIFY_CLIENT_SECRET'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these variables in your .env file or environment.")
        print("See .env.example for reference.")
        return False
    
    return True

def generate_encryption_key():
    """Generate encryption key if not set"""
    if not os.getenv('TOKEN_ENCRYPTION_KEY'):
        from cryptography.fernet import Fernet
        key = Fernet.generate_key().decode()
        print(f"⚠️  Generated encryption key: {key}")
        print("   Add this to your .env file: TOKEN_ENCRYPTION_KEY={key}")
        os.environ['TOKEN_ENCRYPTION_KEY'] = key

def setup_database():
    """Initialize database"""
    try:
        from models import init_database
        init_database()
        print("✅ Database initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False

def main():
    """Main startup function"""
    print("🎵 Spotify MCP Multi-User Server")
    print("=" * 40)
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Check environment configuration
    if not check_environment():
        sys.exit(1)
    
    # Generate encryption key if needed
    generate_encryption_key()
    
    # Setup database
    if not setup_database():
        sys.exit(1)
    
    # Import and run server
    try:
        from spotify_server_multiuser import main as server_main
        server_main()
    except ImportError:
        # Fallback to running the server directly
        print("Running server directly...")
        os.system("python spotify_server_multiuser.py")

if __name__ == "__main__":
    main()
