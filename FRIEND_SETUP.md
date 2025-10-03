# Spotify MCP Server - Quick Setup for Friends

**⚠️ IMPORTANT: You need Claude Pro to use MCP servers. The free version of Claude doesn't support custom connectors.**

## Step 1: Get Your API Key

1. **Visit**: https://6ecabf48ee60.ngrok-free.app/auth/login
2. **Click "Connect to Spotify"** and authorize the app
3. **Copy your API key** from the success page (keep this safe!)

## Step 2: Add to Claude Desktop

1. **Open Claude Desktop**
2. **Go to Settings** → **Connectors**
3. **Click "Add Custom Connector"**
4. **Enter:**
   - **Name**: `Spotify`
   - **URI**: `https://6ecabf48ee60.ngrok-free.app/claude-mcp?token=YOUR_API_KEY_HERE`
   - **Authentication**: None (token included in URL)

**⚠️ IMPORTANT**: Replace `YOUR_API_KEY_HERE` with your actual API key from Step 1!

## Step 3: Test It

Ask Claude: _"Search for Taylor Swift songs"_ or _"What are my Spotify playlists?"_

## Available Commands

- Search for music: _"Find songs by [artist]"_
- Get current playing: _"What's currently playing on Spotify?"_
- List playlists: _"Show my Spotify playlists"_
- Create playlists: _"Create a playlist called [name]"_
- Add songs to playlists: _"Add these songs to my playlist"_

## Troubleshooting

- **No tools showing?** Double-check the URI has your correct API key and that you have Claude Pro
- **Authentication errors?** Re-visit the login URL to get a fresh API key
- **Claude says "raw MCP response"?** This is cosmetic - the data is correct, just displayed differently
- **Other issues?** Contact Geoff

---

_Each person needs their own API key - don't share yours! This server provides complete user isolation._
