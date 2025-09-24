#!/usr/bin/env python3
"""
Entry point for the Hummingbot MCP Server
"""

import argparse
import asyncio

from dotenv import load_dotenv

from hummingbot_mcp import main

load_dotenv()

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Hummingbot MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http", "sse"],
        default=None,
        help="Transport type (default: from .env or stdio)"
    )
    parser.add_argument(
        "--host",
        default=None,
        help="Host address for HTTP transport (default: from .env or 127.0.0.1)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port number for HTTP transport (default: from .env or 8000)"
    )
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    asyncio.run(main(transport=args.transport, host=args.host, port=args.port))
