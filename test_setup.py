#!/usr/bin/env python3
"""
Test script for Spotify MCP Multi-User Server
Verifies database setup and basic functionality
"""

import os
import sys
from pathlib import Path

# Add current directory to Python path
sys.path.append(str(Path(__file__).parent))

def test_imports():
    """Test that all modules can be imported"""
    try:
        print("Testing imports...")
        import models
        import auth
        import spotify_client
        import web_auth
        import middleware
        import spotify_tools
        print("✅ All modules imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_database():
    """Test database initialization"""
    try:
        print("Testing database setup...")
        from models import init_database, get_database_session
        
        # Initialize database
        init_database()
        
        # Test database connection
        db = get_database_session()
        db.close()
        
        print("✅ Database setup successful")
        return True
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def test_encryption():
    """Test token encryption/decryption"""
    try:
        print("Testing encryption...")
        from models import encrypt_token, decrypt_token
        
        test_token = "test_spotify_token_12345"
        encrypted = encrypt_token(test_token)
        decrypted = decrypt_token(encrypted)
        
        if decrypted == test_token:
            print("✅ Token encryption working")
            return True
        else:
            print("❌ Token encryption failed")
            return False
    except Exception as e:
        print(f"❌ Encryption error: {e}")
        return False

def test_auth_utils():
    """Test authentication utilities"""
    try:
        print("Testing auth utilities...")
        from auth import generate_api_key, generate_user_id
        
        api_key = generate_api_key()
        user_id = generate_user_id()
        
        if len(api_key) == 32 and len(user_id) == 36:  # UUID length
            print("✅ Auth utilities working")
            return True
        else:
            print("❌ Auth utilities failed")
            return False
    except Exception as e:
        print(f"❌ Auth utilities error: {e}")
        return False

def main():
    """Run all tests"""
    print("🎵 Spotify MCP Multi-User Server Test Suite")
    print("=" * 50)
    
    # Set up environment for testing
    from cryptography.fernet import Fernet
    os.environ['TOKEN_ENCRYPTION_KEY'] = Fernet.generate_key().decode()
    os.environ['SPOTIFY_CLIENT_ID'] = 'test_client_id'
    os.environ['SPOTIFY_CLIENT_SECRET'] = 'test_client_secret'
    os.environ['DATABASE_URL'] = 'sqlite:///./test_spotify.db'
    
    tests = [
        ("Module Imports", test_imports),
        ("Database Setup", test_database),
        ("Token Encryption", test_encryption),
        ("Auth Utilities", test_auth_utils),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name}...")
        if test_func():
            passed += 1
    
    print(f"\n{'=' * 50}")
    print(f"Tests Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! Multi-user server is ready.")
        print("\nNext steps:")
        print("1. Set your REAL Spotify app credentials in .env file:")
        print("   SPOTIFY_CLIENT_ID=your_real_client_id")
        print("   SPOTIFY_CLIENT_SECRET=your_real_client_secret") 
        print("2. Run: python spotify_server_multiuser.py")
        print("3. Visit: http://localhost:8001/auth/login")
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1
    
    # Clean up test database
    try:
        os.remove('./test_spotify.db')
    except:
        pass
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
