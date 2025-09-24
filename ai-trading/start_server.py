#!/usr/bin/env python3
"""
Startup script for AI Trading Agent with Claude integration
"""
import sys
import os
import asyncio
import logging

# Add the ai-trading directory to Python path
ai_trading_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ai_trading_dir)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_config():
    """Check if configuration file exists"""
    config_file = os.path.join(ai_trading_dir, "config.local.json")
    if not os.path.exists(config_file):
        logger.error(f"Configuration file not found: {config_file}")
        logger.info("Please create config.local.json with your API keys")
        return False
    return True

def main():
    """Main startup function"""
    logger.info("🚀 Starting AI Trading Agent with Claude Integration")
    
    # Check configuration
    if not check_config():
        sys.exit(1)
    
    try:
        # Import after path setup
        from backend.config import get_config
        from backend.api_server import app
        
        # Load configuration
        config = get_config()
        logger.info(f"✅ Configuration loaded")
        logger.info(f"📡 Claude Model: {config.anthropic.model}")
        logger.info(f"🌐 Server: {config.server.host}:{config.server.port}")
        logger.info(f"💰 Hyperliquid: {config.hyperliquid.base_url}")
        
        # Start the server
        import uvicorn
        logger.info("🎯 Starting FastAPI server...")
        
        uvicorn.run(
            "backend.api_server:app",
            host=config.server.host,
            port=config.server.port,
            reload=False,
            workers=4,
            log_level="info"
        )
        
    except FileNotFoundError as e:
        logger.error(f"❌ Configuration error: {e}")
        logger.info("💡 Make sure config.local.json exists with valid API keys")
        sys.exit(1)
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        logger.info("💡 Run: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Startup error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()