"""
Hummingbot V2 Controller Integration
Connects AI Trading Agent to live Hummingbot V2 deployment
"""
import asyncio
import json
import logging
from typing import Dict, Any, Optional
import aiohttp
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class HummingbotV2Controller:
    """
    Integration with Hummingbot V2 Controller API
    Handles strategy deployment and management
    """
    
    def __init__(self, api_url: str = "http://localhost:8000", 
                 username: str = "admin", password: str = "admin"):
        self.api_url = api_url.rstrip('/')
        self.auth = aiohttp.BasicAuth(username, password)
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(auth=self.auth)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def health_check(self) -> bool:
        """Check if Hummingbot V2 API is accessible"""
        try:
            async with aiohttp.ClientSession(auth=self.auth) as session:
                async with session.get(f"{self.api_url}/") as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("status") == "running"
            return False
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    async def get_bot_status(self) -> Dict[str, Any]:
        """Get current bot orchestration status"""
        try:
            async with aiohttp.ClientSession(auth=self.auth) as session:
                async with session.get(f"{self.api_url}/bot-orchestration/status") as response:
                    if response.status == 200:
                        return await response.json()
            return {"status": "error", "data": {}}
        except Exception as e:
            logger.error(f"Failed to get bot status: {e}")
            return {"status": "error", "data": {}}
    
    async def create_controller_config(self, strategy_config: Dict[str, Any]) -> str:
        """Create a controller configuration from AI strategy"""
        config_id = f"ai_strategy_{uuid.uuid4().hex[:8]}"
        
        # Map AI strategy to Hummingbot V2 controller config
        controller_config = self._map_strategy_to_controller(strategy_config, config_id)
        
        try:
            async with aiohttp.ClientSession(auth=self.auth) as session:
                async with session.post(
                    f"{self.api_url}/controllers/configs/{config_id}",
                    json=controller_config
                ) as response:
                    response_text = await response.text()
                    if response.status in [200, 201]:
                        # Check if it contains success message
                        if "saved successfully" in response_text.lower():
                            logger.info(f"Controller config created successfully: {config_id}")
                            return config_id
                        else:
                            logger.warning(f"Unexpected success response: {response_text}")
                            return config_id  # Still return success since status is 200/201
                    else:
                        logger.error(f"Failed to create config (status {response.status}): {response_text}")
                        return None
        except Exception as e:
            logger.error(f"Error creating controller config: {e}")
            return None
    
    async def deploy_strategy(self, config_id: str, instance_name: str = None) -> Dict[str, Any]:
        """Deploy a strategy using V2 controller"""
        if not instance_name:
            instance_name = f"ai_bot_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        deployment_payload = {
            "instance_name": instance_name,
            "credentials_profile": "default",  # This might need configuration
            "controllers_config": [config_id]
        }
        
        try:
            async with aiohttp.ClientSession(auth=self.auth) as session:
                async with session.post(
                    f"{self.api_url}/bot-orchestration/deploy-v2-controllers",
                    json=deployment_payload
                ) as response:
                    if response.status in [200, 201]:
                        result = await response.json()
                        logger.info(f"Strategy deployed: {instance_name}")
                        return {
                            "status": "success",
                            "instance_name": instance_name,
                            "config_id": config_id,
                            "deployment_result": result
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"Deployment failed: {error_text}")
                        return {
                            "status": "error",
                            "error": error_text
                        }
        except Exception as e:
            logger.error(f"Error deploying strategy: {e}")
            return {
                "status": "error", 
                "error": str(e)
            }
    
    async def stop_strategy(self, instance_name: str) -> Dict[str, Any]:
        """Stop a running strategy"""
        try:
            async with aiohttp.ClientSession(auth=self.auth) as session:
                async with session.post(
                    f"{self.api_url}/bot-orchestration/stop-bot",
                    json={"bot_name": instance_name}
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return {"status": "success", "result": result}
                    else:
                        error_text = await response.text()
                        return {"status": "error", "error": error_text}
        except Exception as e:
            logger.error(f"Error stopping strategy: {e}")
            return {"status": "error", "error": str(e)}
    
    async def get_strategy_status(self, instance_name: str) -> Dict[str, Any]:
        """Get status of a specific strategy"""
        try:
            async with aiohttp.ClientSession(auth=self.auth) as session:
                async with session.get(
                    f"{self.api_url}/bot-orchestration/{instance_name}/status"
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return {"status": "not_found"}
        except Exception as e:
            logger.error(f"Error getting strategy status: {e}")
            return {"status": "error", "error": str(e)}
    
    async def list_active_strategies(self) -> Dict[str, Any]:
        """List all active bot runs"""
        try:
            async with aiohttp.ClientSession(auth=self.auth) as session:
                async with session.get(f"{self.api_url}/bot-orchestration/bot-runs") as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return {"status": "error", "data": []}
        except Exception as e:
            logger.error(f"Error listing strategies: {e}")
            return {"status": "error", "data": []}
    
    def _map_strategy_to_controller(self, strategy_config: Dict[str, Any], config_id: str) -> Dict[str, Any]:
        """Map AI-generated strategy to Hummingbot V2 controller format"""
        
        # Extract strategy type and parameters
        strategy_type = strategy_config.get("type", "rsi_directional")
        symbol = strategy_config.get("symbol", "BTC")
        leverage = strategy_config.get("leverage", 3)
        position_size = strategy_config.get("position_size", 1000)
        
        # Determine controller based on strategy type
        if "rsi" in strategy_type.lower() or "directional" in strategy_type.lower():
            controller_config = {
                "id": config_id,
                "controller_name": "dman_v3",
                "controller_type": "directional_trading",
                "total_amount_quote": position_size,
                "connector_name": "hyperliquid",
                "trading_pair": f"{symbol}-USDC",
                "candles_connector": "hyperliquid",
                "candles_trading_pair": f"{symbol}-USDC",
                "leverage": leverage,
                "position_mode": "HEDGE",
                "stop_loss": str(strategy_config.get("stop_loss_pct", 0.03)),
                "take_profit": str(strategy_config.get("take_profit_pct", 0.04)),
                "time_limit": strategy_config.get("time_limit", 3600),
                "max_executors_per_side": 1,
                "cooldown_time": 300,
                "interval": strategy_config.get("rsi_timeframe", "5m"),
                "bb_length": strategy_config.get("rsi_period", 14),
                "bb_std": 2.0,
                "bb_long_threshold": 0.3,  # RSI oversold equivalent
                "bb_short_threshold": 0.7,  # RSI overbought equivalent
                "dca_spreads": "0.0",
            }
        elif "market_making" in strategy_type.lower():
            controller_config = {
                "id": config_id,
                "controller_name": "pmm_simple",
                "controller_type": "market_making",
                "total_amount_quote": position_size,
                "connector_name": "hyperliquid",
                "trading_pair": f"{symbol}-USDC",
                "leverage": leverage,
                "position_mode": "HEDGE",
                "stop_loss": strategy_config.get("stop_loss_pct", 0.05),
                "take_profit": strategy_config.get("take_profit_pct", 0.03),
                "time_limit": 43200,
                "buy_spreads": [strategy_config.get("bid_spread", 0.01)],
                "sell_spreads": [strategy_config.get("ask_spread", 0.01)],
                "buy_amounts_pct": [0.3],
                "sell_amounts_pct": [0.3],
                "executor_refresh_time": strategy_config.get("order_refresh_time", 1800),
                "cooldown_time": 3600,
            }
        else:
            # Default to directional trading
            controller_config = {
                "id": config_id,
                "controller_name": "dman_v3", 
                "controller_type": "directional_trading",
                "total_amount_quote": position_size,
                "connector_name": "hyperliquid",
                "trading_pair": f"{symbol}-USDC",
                "candles_connector": "hyperliquid",
                "candles_trading_pair": f"{symbol}-USDC",
                "leverage": leverage,
                "position_mode": "HEDGE",
                "stop_loss": "0.03",
                "take_profit": "0.04",
                "time_limit": 3600,
                "max_executors_per_side": 1,
                "cooldown_time": 300,
                "interval": "5m",
                "bb_length": 14,
                "bb_std": 2.0,
                "bb_long_threshold": 0.3,  # RSI oversold equivalent
                "bb_short_threshold": 0.7,  # RSI overbought equivalent
                "dca_spreads": "0.0",
            }
        
        return controller_config

# Convenience functions for integration
async def test_hummingbot_connection() -> bool:
    """Test connection to Hummingbot V2 API"""
    async with HummingbotV2Controller() as controller:
        return await controller.health_check()

async def deploy_ai_strategy(strategy_content: str) -> Dict[str, Any]:
    """Deploy an AI-generated strategy to Hummingbot V2"""
    
    # Parse strategy content (this is a simplified parser)
    strategy_config = _parse_strategy_content(strategy_content)
    
    async with HummingbotV2Controller() as controller:
        # Check if Hummingbot is accessible
        if not await controller.health_check():
            return {
                "status": "error",
                "error": "Hummingbot V2 API not accessible"
            }
        
        # Create controller configuration
        config_id = await controller.create_controller_config(strategy_config)
        if not config_id:
            return {
                "status": "error", 
                "error": "Failed to create controller configuration"
            }
        
        # Deploy the strategy
        deployment_result = await controller.deploy_strategy(config_id)
        
        return {
            "status": deployment_result.get("status"),
            "config_id": config_id,
            "instance_name": deployment_result.get("instance_name"),
            "deployment_id": config_id,  # For compatibility with existing API
            "message": "Strategy deployed to Hummingbot V2" if deployment_result.get("status") == "success" else deployment_result.get("error")
        }

def _parse_strategy_content(content: str) -> Dict[str, Any]:
    """Parse strategy content into configuration dict"""
    
    # Simple parser for strategy parameters
    config = {
        "type": "rsi_directional",
        "symbol": "BTC",
        "leverage": 3,
        "position_size": 1000,
        "stop_loss_pct": 0.03,
        "take_profit_pct": 0.04,
        "rsi_period": 14,
        "rsi_timeframe": "5m"
    }
    
    # Extract parameters from content
    lines = content.lower().split('\n')
    for line in lines:
        if 'symbol:' in line or 'asset:' in line:
            parts = line.split(':')
            if len(parts) > 1:
                config["symbol"] = parts[1].strip().upper()
        elif 'leverage:' in line:
            try:
                config["leverage"] = int(line.split(':')[1].strip().replace('x', ''))
            except: pass
        elif 'position' in line and '$' in line:
            try:
                amount_str = line.split('$')[1].split()[0].replace(',', '')
                config["position_size"] = float(amount_str)
            except: pass
        elif 'rsi period:' in line or 'rsi_period:' in line:
            try:
                config["rsi_period"] = int(line.split(':')[1].strip())
            except: pass
        elif 'stop loss:' in line or 'stop_loss:' in line:
            try:
                pct = float(line.split(':')[1].strip().replace('%', '')) / 100
                config["stop_loss_pct"] = pct
            except: pass
    
    return config