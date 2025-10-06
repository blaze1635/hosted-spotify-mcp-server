# AI Agent Instructions for Spotify MCP Multi-User Server

This document provides comprehensive guidance for AI coding agents working on the Spotify MCP Multi-User Server codebase. This system enables multiple users to authenticate with their individual Spotify accounts and access personalized music data through Claude Desktop and other MCP clients.

## 🏗️ Architecture Overview

### Core System Design

- **Multi-User Architecture**: Each user has isolated authentication, token storage, and Spotify API access
- **FastMCP Framework**: Built on FastMCP 2.12.4 with custom routing and middleware capabilities
- **Claude Desktop Compatibility**: Special proxy route (`/claude-mcp`) bypasses middleware limitations
- **Database-Backed**: SQLite (local) or PostgreSQL (production) with encrypted token storage
- **OAuth Flow**: Complete Spotify OAuth 2.0 implementation with secure token management

### Key Components

1. **Main Server** (`spotify_server_multiuser.py`) - Production MCP server with dual-mode support
2. **Authentication System** (`auth.py`, `web_auth.py`) - OAuth flow and API key management
3. **Database Layer** (`models.py`) - User, token, and session management with encryption
4. **Spotify Integration** (`spotify_client.py`, `spotify_tools.py`) - Multi-user Spotify API wrapper
5. **Middleware System** (`middleware.py`) - Authentication middleware for non-Claude clients

## 🔧 Critical Implementation Patterns

### Claude Desktop Compatibility

**CRITICAL**: FastMCP middleware breaks Claude Desktop tool discovery. The system uses two modes:

```python
# Claude Desktop mode (CLAUDE_COMPATIBILITY=true)
- NO middleware - tools handle authentication individually
- /claude-mcp proxy route for token passing
- Tool-level authentication via get_user_from_request()

# MCP Client mode (CLAUDE_COMPATIBILITY=false)
- Full middleware stack with MCPAuthMiddleware
- Request context injection for efficient auth
- Designed for VS Code extensions, CLI tools
```

### OAuth Caching Fix

**CRITICAL BUG RESOLVED**: SpotifyOAuth caching caused user profile mixing:

```python
# ❌ WRONG - Causes token caching and user mixing
auth_manager = SpotifyOAuth(...)  # Uses .cache file

# ✅ CORRECT - Disables caching completely
auth_manager = SpotifyOAuth(..., cache_handler=None)
```

### Multi-Method Token Extraction

The `get_user_from_request()` function uses three methods to extract user tokens:

```python
def get_user_from_request() -> dict:
    # Method 1: Middleware context (CLAUDE_COMPATIBILITY=false)
    if hasattr(mcp, 'request_context') and hasattr(mcp.request_context, 'user_context'):
        return mcp.request_context.user_context

    # Method 2: Direct token storage (Claude Desktop via /claude-mcp)
    if hasattr(mcp, '_current_request_token'):
        token = mcp._current_request_token
        return get_user_by_api_key(token)

    # Method 3: Global token fallback
    if hasattr(mcp, '_global_user_token'):
        token = mcp._global_user_token
        return get_user_by_api_key(token)
```

## 📁 File Structure & Responsibilities

### Production Files

- `spotify_server_multiuser.py` - **Main production server**

  - FastMCP server initialization with dual-mode support
  - Claude Desktop proxy route `/claude-mcp`
  - All MCP tool definitions with user context injection
  - Middleware configuration based on CLAUDE_COMPATIBILITY flag

- `models.py` - **Database schema and encryption**

  - SQLAlchemy models: User, SpotifyToken, UserSession
  - Fernet encryption for token storage (`encrypt_token`, `decrypt_token`)
  - Database session management and initialization

- `auth.py` - **Core authentication utilities**

  - API key generation and validation
  - User lookup functions (`get_user_by_api_key`)
  - Session cleanup and management

- `web_auth.py` - **OAuth web routes**

  - `/auth/login` - Initiate Spotify OAuth
  - `/auth/callback` - Handle OAuth callback
  - `/auth/status` - Check authentication status
  - `/auth/revoke` - Revoke user access

- `spotify_client.py` - **Spotify API management**

  - `SpotifyUserManager` class for multi-user token handling
  - **CRITICAL**: OAuth with `cache_handler=None` to prevent caching
  - Automatic token refresh and error handling

- `spotify_tools.py` - **MCP tool implementations**
  - All Spotify tools with user context parameter
  - User-specific Spotify client retrieval
  - Error handling with user identification

### Legacy/Backup Files

- `spotify_singleuser_backup.py` - Backup of original single-user architecture (keep for reference)
- `temp_quickbooks_server.py` - Unrelated QuickBooks server (can be ignored)

## 🔐 Security & Authentication Patterns

### Token Encryption

All Spotify tokens are encrypted at rest using Fernet (AES 128 CBC + HMAC):

```python
# Encryption setup in models.py
ENCRYPTION_KEY = os.getenv("TOKEN_ENCRYPTION_KEY")
cipher_suite = Fernet(ENCRYPTION_KEY.encode())

def encrypt_token(token: str) -> str:
    return cipher_suite.encrypt(token.encode()).decode()

def decrypt_token(encrypted_token: str) -> str:
    return cipher_suite.decrypt(encrypted_token.encode()).decode()
```

### API Key System

- 32-character cryptographically secure API keys
- Unique per user, stored in database
- Used as Bearer tokens in Claude Desktop
- Automatic cleanup of expired sessions

### OAuth State Validation

- CSRF protection in OAuth flow
- State parameter validation in callbacks
- Secure session management

## 🌐 Deployment & Environment

### Environment Variables

```bash
# Required for production
SPOTIFY_CLIENT_ID=your_client_id
SPOTIFY_CLIENT_SECRET=your_client_secret
SPOTIFY_REDIRECT_URI=https://your-domain.com/auth/callback
TOKEN_ENCRYPTION_KEY=your_fernet_key
DATABASE_URL=postgresql://user:pass@host/db

# Configuration flags
CLAUDE_COMPATIBILITY=true  # Enable Claude Desktop mode
ENVIRONMENT=prod
TRANSPORT=http
DEPLOYMENT=render
```

### Database Configuration

- **Local Development**: SQLite with `sqlite:///./spotify_users.db`
- **Production**: PostgreSQL with automatic URL format conversion
- **Migrations**: SQLAlchemy models with `Base.metadata.create_all()`

### Ngrok Integration (Development)

- Production server runs on ngrok tunnel for Claude Desktop access
- Tunnel URL: `https://6ecabf48ee60.ngrok-free.app`
- Claude Desktop configuration uses `/claude-mcp` proxy route

## 🛠️ Development Workflows

### Adding New Spotify Tools

1. Create implementation in `spotify_tools.py` with `user_context` parameter
2. Add MCP tool decorator in `spotify_server_multiuser.py`
3. Call `get_user_from_request()` for authentication
4. Pass user context to implementation function

Example:

```python
@mcp.tool
def new_spotify_feature(param: str) -> str:
    """New Spotify feature description"""
    user_context = get_user_from_request()
    return new_spotify_feature_impl(param, user_context)
```

### Testing Multi-User Functionality

1. Start server with `python spotify_server_multiuser.py`
2. Multiple users visit `/auth/login` to get API keys
3. Configure Claude Desktop with different API keys
4. Verify complete data isolation between users

### Debugging Authentication Issues

1. Check `CLAUDE_COMPATIBILITY` environment variable
2. Verify OAuth callback URL configuration
3. Monitor token extraction in `get_user_from_request()`
4. Check database for encrypted token storage
5. Ensure `cache_handler=None` in SpotifyOAuth calls

## 📊 Database Schema Patterns

### User Table

```python
User:
  - user_id (UUID primary key)
  - api_key (unique 32-char string)
  - spotify_user_id (from Spotify profile)
  - display_name, email (profile data)
  - created_at, last_active (timestamps)
```

### Token Storage

```python
SpotifyToken:
  - user_id (foreign key to User)
  - access_token (encrypted with Fernet)
  - refresh_token (encrypted with Fernet)
  - expires_at (datetime for refresh logic)
  - scope (Spotify permissions)
```

### Session Management

```python
UserSession:
  - session_id (unique identifier)
  - user_id (foreign key to User)
  - api_key (for quick lookup)
  - created_at, expires_at (lifecycle)
```

## ⚠️ Common Pitfalls & Solutions

### Middleware Compatibility

- **Problem**: ANY middleware breaks Claude Desktop tool discovery
- **Solution**: Use `CLAUDE_COMPATIBILITY=true` and `/claude-mcp` proxy route

### OAuth Token Caching

- **Problem**: SpotifyOAuth caches tokens causing user mixing
- **Solution**: Always use `cache_handler=None` in SpotifyOAuth initialization

### Multi-User Context Loss

- **Problem**: Tools losing user context between calls
- **Solution**: Implement `get_user_from_request()` with multiple fallback methods

### Token Refresh Failures

- **Problem**: Expired tokens not refreshing properly
- **Solution**: Use `SpotifyUserManager.get_user_spotify_client()` with built-in refresh

## 🔄 Integration Points

### Claude Desktop Integration

- URL: `https://your-domain.com/claude-mcp?token=USER_API_KEY`
- Method: Query parameter token passing
- Proxy: Internal forwarding to `/mcp` endpoint
- Timeout: 30-second timeout handling

### Spotify API Integration

- All requests go through user-specific `spotipy.Spotify` clients
- Automatic token refresh using encrypted refresh tokens
- Scope management for playlist, playback, and profile access
- Error handling with user-friendly messages

### Database Integration

- SQLAlchemy ORM with relationship management
- Automatic encryption/decryption of sensitive data
- Session cleanup and lifecycle management
- Migration support through model updates

## 📚 Documentation References

- `README_MULTIUSER.md` - Complete setup and usage guide
- `FRIEND_SETUP.md` - User onboarding instructions
- `IMPLEMENTATION_COMPLETE.md` - Technical implementation details
- `CURRENT_STATUS_AND_CONTEXT.md` - VS Code restart continuity

## 🎯 Key Success Metrics

### Multi-User Isolation

- ✅ Complete user data separation confirmed
- ✅ Concurrent user testing with Ali Claire + gcblaisdell
- ✅ Independent playlist creation and access

### Claude Desktop Compatibility

- ✅ Tool discovery working without middleware
- ✅ Proxy route handling all HTTP methods (GET/POST/DELETE)
- ✅ Token parameter extraction and forwarding

### Production Readiness

- ✅ Encrypted token storage with Fernet
- ✅ Automatic session cleanup and token refresh
- ✅ Comprehensive error handling and logging
- ✅ Environment-based configuration management

---

**Remember**: This is a production system with real users. Always test authentication flows, verify user isolation, and maintain the critical OAuth caching fix (`cache_handler=None`) when making changes.
