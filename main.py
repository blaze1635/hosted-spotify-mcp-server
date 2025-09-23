#!/usr/bin/env python3
"""
Railway entry point for Hosted Spotify MCP Server
"""

import os
from spotify_server import mcp

# Railway provides PORT environment variable
port = int(os.environ.get("PORT", 8000))

if __name__ == "__main__":
    print("🚀 Starting Spotify MCP Server on Railway...")
    print(f"🌐 Running on port {port}")
    
    # Run the FastMCP server with Railway's port
    mcp.run(transport="sse", host="0.0.0.0", port=port)