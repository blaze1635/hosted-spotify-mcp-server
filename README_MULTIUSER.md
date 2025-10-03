# Spotify MCP Multi-User Server

A production-ready multi-user Model Context Protocol (MCP) server that provides Spotify integration for Claude Desktop and other MCP clients. Each user can authenticate with their own Spotify account and get completely isolated access to their music data.

## Features

- **✅ True Multi-User Support**: Multiple users can authenticate and use the server simultaneously with complete data isolation
- **🔐 Secure Authentication**: OAuth 2.0 flow with Spotify + API key authentication for MCP
- **🔒 Token Encryption**: All Spotify tokens are encrypted at rest
- **🔄 Automatic Token Refresh**: Handles expired tokens transparently
- **☁️ Local & Cloud Deployment**: Works locally with SQLite or in production with PostgreSQL
- **📱 Session Management**: Persistent user sessions with automatic cleanup
- **🖥️ Claude Desktop Compatible**: Special proxy route for Claude Desktop MCP integration
- **🚫 OAuth Caching Fix**: Eliminates token caching issues that cause user profile mixing

## Quick Start

### 1. Local Development Setup

```bash
# Clone and setup
git clone <your-repo>
cd hosted-spotify-mcp-server

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env file with your Spotify app credentials:
# - SPOTIFY_CLIENT_ID=your_client_id
# - SPOTIFY_CLIENT_SECRET=your_client_secret
# - BASE_URL=your_ngrok_or_production_url
```

### 2. Create Spotify App

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create a new app
3. Add redirect URI: `http://localhost:8001/auth/callback` (for local testing)
4. Add users to your app under "Users and Access" for Development Mode
5. Copy Client ID and Client Secret to your `.env` file

### 3. Start the Server

```bash
# Start in HTTP mode for multi-user support
python spotify_server_multiuser.py

# Server will be available at:
# - Local: http://localhost:8001
# - Authentication: /auth/login
# - MCP Endpoint: /claude-mcp (for Claude Desktop)
```

### 4. Authenticate Users

1. Visit: `http://localhost:8001/auth/login`
2. Log in with Spotify account
3. Copy the provided API key
4. Configure Claude Desktop with:
   - **URL**: `http://localhost:8001/mcp`
   - **Authentication**: Bearer Token
   - **Token**: `<your-api-key>`

## File Structure

```
├── spotify_server_multiuser.py    # Main multi-user MCP server
├── spotify_singleuser_backup.py    # Backup of original single-user version
├── models.py                      # Database models (User, SpotifyToken, UserSession)
├── auth.py                        # Authentication utilities and API key management
├── spotify_client.py              # Spotify client management and token refresh
├── web_auth.py                    # OAuth flow and web authentication routes
├── middleware.py                  # MCP authentication middleware
├── spotify_tools.py               # Multi-user Spotify tools implementation
├── start_server.py                # Startup script with environment checks
├── requirements.txt               # Python dependencies
├── render.yaml                    # Production deployment configuration
├── .env.example                   # Environment variables template
└── README.md                      # This file
```

## Available Tools

All tools now support per-user authentication:

- **`search_tracks(query, limit=5)`** - Search Spotify for songs, artists, albums
- **`get_current_track()`** - Get currently playing track for the user
- **`get_user_playlists(limit=10)`** - List user's Spotify playlists
- **`create_playlist(name, description="", public=false)`** - Create new playlist
- **`add_tracks_to_playlist(playlist_id, track_uris)`** - Add songs to playlist

## Architecture

### Authentication Flow

1. **User Registration**: Users visit `/auth/login` → Spotify OAuth → Get API key
2. **MCP Authentication**: Claude Desktop uses API key as Bearer token
3. **Request Processing**: Middleware validates API key → Tools get user context
4. **Spotify API Calls**: User-specific Spotify client with auto-refreshed tokens

### Database Schema

```python
# User table
User:
  - user_id (primary key)
  - api_key (unique)
  - spotify_user_id
  - display_name
  - created_at, last_active

# Encrypted token storage
SpotifyToken:
  - user_id (foreign key)
  - access_token (encrypted)
  - refresh_token (encrypted)
  - expires_at
  - scope

# Session management
UserSession:
  - session_id
  - user_id
  - api_key
  - created_at, expires_at
```

### Security Features

- **Token Encryption**: All tokens encrypted with Fernet (AES 128 CBC + HMAC)
- **Secure API Keys**: 32-character cryptographically secure keys
- **Session Expiry**: 30-day session lifetime with automatic cleanup
- **OAuth State Validation**: CSRF protection in OAuth flow
- **Minimal Data Storage**: Only necessary user information stored

## Deployment

### Local Development

```bash
# SQLite database (automatic)
TRANSPORT=http python spotify_server_multiuser.py
```

### Production (Render)

1. **Database Setup**:

   - Create PostgreSQL service on Render
   - Update `DATABASE_URL` environment variable

2. **Environment Variables**:

   ```bash
   ENVIRONMENT=prod
   TRANSPORT=http
   DATABASE_URL=postgresql://...
   TOKEN_ENCRYPTION_KEY=<generated-key>
   SESSION_SECRET_KEY=<random-key>
   SPOTIFY_CLIENT_ID=<your-client-id>
   SPOTIFY_CLIENT_SECRET=<your-client-secret>
   SPOTIFY_REDIRECT_URI=https://your-domain.onrender.com/auth/callback
   ```

3. **Deploy**:
   - Push to Git repository
   - Deploy via Render dashboard or `render.yaml`

## Environment Variables

### Required

- `SPOTIFY_CLIENT_ID` - Your Spotify app client ID
- `SPOTIFY_CLIENT_SECRET` - Your Spotify app client secret

### Optional

- `DATABASE_URL` - Database connection (defaults to SQLite)
- `TOKEN_ENCRYPTION_KEY` - Token encryption key (auto-generated in dev)
- `SESSION_SECRET_KEY` - Session middleware secret
- `SPOTIFY_REDIRECT_URI` - OAuth callback URL (auto-configured)
- `TRANSPORT` - `http` or `stdio` (default: `stdio`)
- `ENVIRONMENT` - `dev` or `prod` (default: `dev`)
- `HOST` - Server host (default: `0.0.0.0`)
- `PORT` - Server port (default: `8001`)

## Testing Multiple Users

1. **First User**:

   - Visit `http://localhost:8001/auth/login`
   - Authenticate → Get API Key A
   - Configure Claude Desktop with API Key A

2. **Second User**:

   - Visit `http://localhost:8001/auth/login` (different browser/incognito)
   - Authenticate with different Spotify account → Get API Key B
   - Configure second Claude Desktop instance with API Key B

3. **Verify Isolation**:
   - Each user sees only their own playlists, currently playing track, etc.
   - Tools work independently for each user

## Troubleshooting

### "No user context provided"

- Ensure you're using Bearer token authentication in Claude Desktop
- Verify your API key is correct (get a new one from `/auth/login`)

### "Failed to get Spotify client"

- Your Spotify tokens may have expired and failed to refresh
- Re-authenticate at `/auth/login`

### Database errors

- Check `DATABASE_URL` format
- For SQLite: ensure write permissions in directory
- For PostgreSQL: verify connection string

### Import errors

- Install all dependencies: `pip install -r requirements.txt`
- Check Python version compatibility

## Development

### Adding New Tools

1. Implement in `spotify_tools.py`:

   ```python
   def new_tool_impl(param1: str, user_context: Dict[str, Any] = None) -> str:
       sp = get_user_spotify_client_for_tool(user_context)
       # Your implementation
   ```

2. Register in `spotify_server_multiuser.py`:
   ```python
   @mcp.tool
   def new_tool(param1: str) -> str:
       user_context = getattr(mcp.request_context, 'user_context', None)
       return new_tool_impl(param1, user_context)
   ```

### Database Migrations

For production, consider using Alembic for schema migrations:

```bash
pip install alembic
alembic init migrations
alembic revision --autogenerate -m "Initial tables"
alembic upgrade head
```

## Migration from Single-User

The original single-user server is backed up as `spotify_singleuser_backup.py`. To migrate:

1. Existing single-user deployments continue working
2. New multi-user server runs on same endpoints
3. Users need to authenticate once to get API keys
4. Update Claude Desktop configuration to use Bearer token authentication

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with proper error handling
4. Test with multiple users
5. Submit pull request

## License

MIT License - see LICENSE file for details.
