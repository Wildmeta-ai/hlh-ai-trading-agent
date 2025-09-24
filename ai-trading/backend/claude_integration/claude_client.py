import anthropic
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

# Fallback configuration classes
@dataclass
class AnthropicConfig:
    api_key: str = "mock-key"
    model: str = "claude-3-5-sonnet-20241022"
    max_tokens: int = 4096
    claude_api_url: str = "http://localhost:9655"

@dataclass
class BotConfig:
    base_url: str = "http://15.235.212.36:8091"

@dataclass
class ServerConfig:
    host: str = "localhost"
    port: int = 8000
    cors_origins: Optional[list] = None

@dataclass
class HyperliquidConfig:
    api_wallet: str = "mock-wallet"
    api_key: str = "mock-key"
    base_url: str = "https://api.hyperliquid.xyz"

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

_fallback_config = Config(
    anthropic=AnthropicConfig(),
    hyperliquid=HyperliquidConfig(),
    server=ServerConfig(),
    bot=BotConfig(),
    mcp=MCPConfig()
)

def _get_fallback_config():
    return _fallback_config

# Import configuration with fallback
try:
    from ..config import get_config
except ImportError:
    try:
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        from config import get_config  # type: ignore
    except ImportError:
        get_config = _get_fallback_config

logger = logging.getLogger(__name__)


class ClaudeClient:
    """Basic Claude API Client"""

    def __init__(self):
        self.config = get_config()
        self.client = anthropic.Anthropic(
            base_url=self.config.anthropic.claude_api_url,
            api_key=self.config.anthropic.api_key,
            max_retries=0,  # Disable automatic retries
            timeout=None    # Disable timeout (never timeout)
        )
        logger.info("Claude client initialized")

    async def create_message(
        self,
        messages: List[Dict[str, Any]],
        system: str = "",
        tools: Optional[List[Dict[str, Any]]] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        enable_mcp: Optional[bool] = True
    ) -> Any:
        """Create Claude message"""
        try:
            params = {
                "model": model or self.config.anthropic.model,
                "max_tokens": max_tokens or self.config.anthropic.max_tokens,
                "messages": messages,
                "mcp_servers": [],
                "timeout": 600,
            }

            if enable_mcp:
                config = get_config()
                mcp_servers = params["mcp_servers"]
                if isinstance(mcp_servers, list):
                    mcp_servers.append({
                        "name": "hummingbot",
                        "type": "url",
                        "url": config.mcp.url,
                    })

            if system:
                params["system"] = system

            if tools:
                params["tools"] = tools

            if temperature is not None:
                params["temperature"] = temperature

            response = self.client.beta.messages.create(**params)
            logger.info(
                f"Claude API call successful, model: {params['model']}")
            return response

        except Exception as e:
            logger.error(f"Claude API call failed: {e}")
            raise

    def get_model_info(self) -> Dict[str, Any]:
        """Get model configuration information"""
        return {
            "model": self.config.anthropic.model,
            "max_tokens": self.config.anthropic.max_tokens,
            "api_key_configured": bool(self.config.anthropic.api_key)
        }
