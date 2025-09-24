#!/usr/bin/env python3
"""
HTTP MCP Server for Hummingbot
Runs the MCP server in streamable-http mode for URL-based access
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_config():
    """Get server configuration from environment variables"""
    host = os.getenv("MCP_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_PORT", "8000"))
    ssl_enabled = os.getenv("SSL_ENABLED", "false").lower() == "true"
    return host, port, ssl_enabled

if __name__ == "__main__":
    from hummingbot_mcp.server import main
    
    host, port, ssl_enabled = get_config()
    protocol = "https" if ssl_enabled else "http"
    print(f"Starting Hummingbot MCP Server in streamable-http mode...")
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Protocol: {protocol}")
    print(f"MCP Server will be accessible via streamable-http transport")
    print(f"Server URL: {protocol}://{host}:{port}/mcp")
    if ssl_enabled:
        print("SSL is enabled - ensure SSL_CERT_FILE and SSL_KEY_FILE are configured")
    print("Use HTTP transport in your MCP client configuration")
    
    asyncio.run(main(transport="streamable-http", host=host, port=port))