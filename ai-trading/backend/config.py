"""
Configuration management for AI Trading Agent
"""
import json
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class AnthropicConfig:
    api_key: str
    model: str = "claude-3-5-sonnet-20241022"
    max_tokens: int = 4096
    claude_api_url: str = "http://localhost:9655"

@dataclass
class HyperliquidConfig:
    api_wallet: str
    api_key: str
    base_url: str = "https://api.hyperliquid.xyz"

@dataclass
class ServerConfig:
    host: str = "localhost"
    port: int = 8000
    cors_origins: Optional[list] = None

@dataclass
class BotConfig:
    base_url: str = "http://15.235.212.36:8091"

@dataclass
class MCPConfig:
    url: str = "http://127.0.0.1:8002/mcp"

@dataclass
class Config:
    anthropic: AnthropicConfig
    hyperliquid: HyperliquidConfig
    server: ServerConfig
    bot: BotConfig
    mcp: MCPConfig

def load_config(config_path: str = "config.local.json") -> Config:
    """Load configuration from local config file"""
    
    # Get the directory where this script is located
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    config_file = os.path.join(project_root, config_path)
    
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"Config file not found: {config_file}")
    
    with open(config_file, 'r') as f:
        config_data = json.load(f)
    
    # Create config objects
    anthropic_config = AnthropicConfig(**config_data["anthropic"])
    hyperliquid_config = HyperliquidConfig(**config_data["hyperliquid"])
    
    server_data = config_data.get("server", {})
    if server_data.get("cors_origins") is None:
        server_data["cors_origins"] = ["http://localhost:3000", "http://localhost:3001"]
    server_config = ServerConfig(**server_data)
    
    bot_data = config_data.get("bot", {})
    bot_config = BotConfig(**bot_data)
    
    mcp_data = config_data.get("mcp", {})
    mcp_config = MCPConfig(**mcp_data)
    
    return Config(
        anthropic=anthropic_config,
        hyperliquid=hyperliquid_config,
        server=server_config,
        bot=bot_config,
        mcp=mcp_config
    )

# Global config instance
_config: Optional[Config] = None

def get_config() -> Config:
    """Get global configuration instance"""
    global _config
    if _config is None:
        _config = load_config()
    return _config