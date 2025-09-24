#!/usr/bin/env python3
"""
Startup script for AI Trading Backend Server
Handles imports and starts the FastAPI server
"""
import os
import sys
import uvicorn

# Add the current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
sys.path.insert(0, os.path.join(current_dir, 'backend'))

if __name__ == "__main__":
    # Import and start the server
    from backend.config import get_config
    
    try:
        config = get_config()
        print(f"Starting AI Trading Agent API server...")
        print(f"Claude model: {config.anthropic.model}")
        print(f"Server: {config.server.host}:{config.server.port}")
        
        # Start uvicorn server
        uvicorn.run(
            "backend.api_server:app",
            host=config.server.host,
            port=config.server.port,
            reload=True,
            log_level="info"
        )
    except Exception as e:
        print(f"Failed to start server: {e}")
        sys.exit(1)