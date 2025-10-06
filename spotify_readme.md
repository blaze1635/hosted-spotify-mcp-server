# Spotify MCP Server - Multi-User Authentication Guide

## 1. User Setup and Authentication Process

### Overview

To use the Spotify MCP Server with Claude Desktop or ChatGPT, users need to complete a one-time setup process to authorize the server to access their Spotify account.

### User Journey

#### Step 1: Initial Setup

1. **User visits authentication URL**: `https://hosted-spotify-mcp-server.onrender.com/auth/login`
2. **System generates unique user session** and redirects to Spotify OAuth
3. **User authorizes the application** on Spotify's authorization page
4. **User grants permissions** for:
   - Reading library and playlists
   - Reading current playback state
   - Creating and modifying playlists
5. **System receives callback** and stores user tokens securely
6. **User receives unique API key/token** for MCP access

#### Step 2: Configure Claude Desktop/ChatGPT

1. **Add MCP connector** in Claude Desktop settings:
   - **URL**: `https://hosted-spotify-mcp-server.onrender.com/mcp`
   - **Authentication**: Bearer token (provided from Step 1)
2. **Test connection** by asking Claude to search for music or check current playing track

#### Step 3: Usage

- Users can now use Spotify tools through Claude Desktop
- Authentication is handled automatically using stored tokens
- Tokens are refreshed automatically when needed
- Users can revoke access anytime through their Spotify account settings

### Available Tools

- `search_tracks` - Search for songs, artists, albums
- `get_current_track` - See what's currently playing
- `get_user_playlists` - List user's playlists
- `create_playlist` - Create new playlists
- `add_tracks_to_playlist` - Add songs to playlists

---

## 2. Technical Implementation Requirements

### Current State

- ✅ Single-user authentication working locally
- ✅ MCP server deployed to Render
- ✅ HTTP transport working
- ✅ Health check endpoint functional

### Required Technical Changes

#### A. Multi-User Authentication System

**1. User Session Management**

```python
# New database models needed
class User:
    - user_id (unique)
    - spotify_user_id
    - display_name
    - email
    - created_at
    - last_active

class SpotifyToken:
    - user_id (foreign key)
    - access_token (encrypted)
    - refresh_token (encrypted)
    - expires_at
    - scope
```

**2. Authentication Endpoints**

- `GET /auth/login` - Initiate OAuth flow with unique state parameter
- `GET /auth/callback` - Handle Spotify OAuth callback
- `GET /auth/status` - Check user authentication status
- `POST /auth/refresh` - Refresh expired tokens
- `DELETE /auth/revoke` - Revoke user access

**3. API Key System**

- Generate unique API keys for each authenticated user
- Map API keys to user sessions
- Include API key validation middleware for MCP endpoints

#### B. Database Integration

**1. Database Setup**

- Add PostgreSQL database (Render supports this)
- Use SQLAlchemy ORM for database operations
- Implement database migrations

**2. Token Storage Security**

- Encrypt tokens at rest using Fernet (cryptography library)
- Use environment variable for encryption key
- Implement secure token retrieval and refresh

#### C. Modified MCP Architecture

**1. User Context in Tools**

```python
# All tools need user context
@mcp.tool
def search_tracks(query: str, limit: int = 5, user_context: dict = None) -> str:
    # Get user-specific Spotify client
    sp = get_user_spotify_client(user_context['user_id'])
    # ... rest of implementation
```

**2. Authentication Middleware**

- Validate API keys on all MCP requests
- Extract user context from API key
- Pass user context to all tool functions

**3. Error Handling**

- Handle expired tokens gracefully
- Return clear error messages for unauthenticated requests
- Provide re-authentication instructions

#### D. Environment Configuration

**1. Additional Environment Variables**

```bash
# Database
DATABASE_URL=postgresql://...

# Encryption
TOKEN_ENCRYPTION_KEY=...

# Spotify App (multi-user)
SPOTIFY_CLIENT_ID=...
SPOTIFY_CLIENT_SECRET=...
SPOTIFY_REDIRECT_URI=https://hosted-spotify-mcp-server.onrender.com/auth/callback

# API Configuration
API_KEY_LENGTH=32
TOKEN_EXPIRY_BUFFER=300  # seconds
```

#### E. Required Dependencies

**1. New Python Packages**

```
sqlalchemy
alembic
psycopg2-binary
cryptography
python-jose
passlib
```

**2. Database Migrations**

- Set up Alembic for database schema management
- Create initial migration for user and token tables

#### F. Frontend/UI Considerations

**1. Authentication Flow UI**

- Simple web pages for login flow
- Success/error pages after OAuth
- API key display and management
- User dashboard for token management

**2. Documentation**

- User setup instructions
- API key usage guide
- Troubleshooting guide

#### G. Deployment Changes

**1. Render Configuration**

- Add PostgreSQL database service
- Update environment variables
- Configure domain for OAuth callbacks

**2. Monitoring and Logging**

- Add user activity logging
- Monitor token refresh rates
- Track API usage per user

### Implementation Priority

**Phase 1 (Core Multi-User Support)**

1. Database setup and models
2. User authentication endpoints
3. Token encryption and storage
4. API key system

**Phase 2 (MCP Integration)**

1. Authentication middleware
2. User context in tools
3. Modified tool implementations

**Phase 3 (Polish)**

1. Frontend UI
2. Documentation
3. Error handling improvements
4. Monitoring and analytics

### Security Considerations

- **Token Encryption**: All tokens encrypted at rest
- **API Key Security**: Secure random generation, rate limiting
- **OAuth State Verification**: Prevent CSRF attacks
- **Token Scope Limitation**: Minimal required Spotify permissions
- **User Data Privacy**: Store only necessary user information
- **Regular Security Audits**: Review token storage and access patterns

---

## Next Steps

1. **Choose database solution** (PostgreSQL on Render recommended)
2. **Implement user authentication system**
3. **Create API key management**
4. **Modify existing tools for multi-user support**
5. **Test with multiple users**
6. **Deploy and document user setup process**

This architecture will allow multiple users to safely authenticate with their own Spotify accounts while using the shared MCP server infrastructure.

---

## 3. Multi-Account Support Design (Option C - Handle-Based Authentication)

### Overview

To enable users to manage multiple Spotify accounts (personal, work, family, etc.) from within a single Claude Desktop conversation, we will implement a handle-based authentication system that provides secure indirection between Claude and actual Spotify tokens.

### Security Model: Handle-Based Indirection

**Problem**: Users want to manage multiple Spotify accounts but putting raw tokens in Claude chat exposes sensitive credentials in conversation history.

**Solution**: Use secure handles that map to tokens server-side, so Claude never sees actual Spotify access tokens.

### User Experience Flow

#### Phase 1: Account Registration

1. **User authenticates each account via OAuth**:

   - `/auth/login?account_name=personal` → User completes Spotify OAuth
   - `/auth/login?account_name=work` → User completes Spotify OAuth
   - `/auth/login?account_name=mom` → User completes Spotify OAuth

2. **System generates secure handles**:
   - After each OAuth completion: "Your 'personal' account is registered as handle: `personal_h4x8k2m9`"
   - Handles are short, secure identifiers that map to encrypted tokens server-side

#### Phase 2: Claude Integration

1. **User registers handles with Claude**:

   ```
   User: "Hey Claude, I want to work with multiple Spotify accounts.
          Add my personal account with handle 'personal_h4x8k2m9'
          and my work account with handle 'work_j8n5p1q3'"
   ```

2. **Claude calls registration tool**:
   - Claude uses MCP tool: `register_account_handle(name="personal", handle="personal_h4x8k2m9")`
   - Server validates handle exists and belongs to authenticated user
   - Server stores mapping: user session → account name → handle

#### Phase 3: Multi-Account Operations

1. **Explicit account switching**:

   ```
   User: "Switch to my work account"
   Claude: Calls switch_account(account="work")
   Result: "Now using work account (work_j8n5p1q3)"
   ```

2. **Contextual account usage**:

   ```
   User: "Search for focus music on my work account"
   Claude: Calls search_tracks(query="focus music", account="work")
   ```

3. **Session-based context memory**:
   ```
   User: "Let's work with my personal account for a while"
   User: "What's currently playing?"  ← Uses personal account automatically
   User: "Create a playlist called 'Road Trip'"  ← Uses personal account
   ```

### Technical Implementation Plan

#### Database Schema Extensions

```python
class SpotifyAccount:
    account_id: str          # UUID
    user_id: str             # Foreign key to User
    account_name: str        # User-defined name ("personal", "work")
    account_handle: str      # Secure handle ("personal_h4x8k2m9")
    spotify_user_id: str     # Spotify's user ID
    display_name: str        # From Spotify profile
    access_token: str        # Encrypted Spotify token
    refresh_token: str       # Encrypted Spotify refresh token
    expires_at: datetime
    created_at: datetime
    is_primary: bool         # Default account for user

class UserSession:
    session_id: str          # From MCP session
    user_id: str
    current_account_handle: str  # Currently active account
    registered_handles: dict     # Maps account names to handles
    last_activity: datetime
```

#### New MCP Tools

```python
@mcp.tool()
def register_account_handle(name: str, handle: str) -> str:
    """Register a Spotify account handle for use in this session"""
    # Validate handle belongs to authenticated user
    # Store in session context
    # Return confirmation

@mcp.tool()
def switch_account(account: str) -> str:
    """Switch to a different registered Spotify account"""
    # Look up handle from account name
    # Set as current account in session
    # Return current account info

@mcp.tool()
def list_accounts() -> str:
    """List all registered accounts for this session"""
    # Return account names and basic info
```

#### Modified Existing Tools

```python
@mcp.tool()
def search_tracks(query: str, limit: int = 5, account: str = None) -> str:
    """Search tracks, optionally specifying account"""
    # If account specified, use that handle
    # Otherwise use current session account
    # Look up tokens from handle
    # Execute Spotify API call

# Similar updates for:
# - get_current_track(account=None)
# - get_user_playlists(account=None)
# - create_playlist(name, account=None)
# - add_tracks_to_playlist(playlist_id, track_ids, account=None)
```

#### Authentication Flow Updates

```python
@app.get("/auth/login")
async def login(account_name: str = "default"):
    """Initiate OAuth for named account"""
    # Include account_name in OAuth state
    # Generate handle preview: f"{account_name}_{random_suffix}"

@app.get("/auth/callback")
async def callback(code: str, state: str):
    """Handle OAuth callback with account context"""
    user_id, account_name = parse_state(state)
    tokens = exchange_tokens(code)
    handle = generate_secure_handle(account_name)

    # Store account with handle
    save_account(user_id, account_name, handle, tokens)

    return f"Account '{account_name}' registered as handle: {handle}"
```

#### Security Features

1. **Handle Validation**: Handles are cryptographically secure and user-scoped
2. **Token Isolation**: Claude never sees raw Spotify tokens
3. **Session Scoping**: Handle registrations are per-MCP session
4. **Audit Logging**: Track handle usage and account switches
5. **Handle Rotation**: Handles can be regenerated without affecting Claude

### Implementation Priority

1. **Phase 1**: Multi-account OAuth registration with handle generation
2. **Phase 2**: Handle-based MCP tools (register, switch, list accounts)
3. **Phase 3**: Update existing tools to support account parameter
4. **Phase 4**: Session-based context management and memory
5. **Phase 5**: Web UI for handle management and account oversight

### Benefits

- **Security**: No sensitive tokens in Claude conversation history
- **Flexibility**: Support unlimited Spotify accounts per user
- **User Experience**: Natural conversation flow with account switching
- **Enterprise Ready**: Secure enough for business/family use cases
- **Maintainable**: Clean separation between authentication and usage
