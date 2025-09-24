#!/usr/bin/env python3
"""
SSE MCP Server for Hummingbot
Runs the MCP server in SSE mode for Server-Sent Events access
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
    return host, port

if __name__ == "__main__":
    from hummingbot_mcp.server import main
    
    host, port = get_config()
    print(f"Starting Hummingbot MCP Server in SSE mode...")
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"MCP Server will be accessible via SSE transport")
    print("Use SSE transport in your MCP client configuration")
    
    asyncio.run(main(transport="sse", host=host, port=port))