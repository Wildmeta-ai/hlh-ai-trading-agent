"""
MCP Server for AI Trading Agent
Provides tools for strategy management, backtesting, and trading execution
"""
import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
import uuid

import sys
import importlib.util
import os

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Import hyperliquid_connector
connector_spec = importlib.util.spec_from_file_location("hyperliquid_connector", os.path.join(current_dir, "hyperliquid_connector.py"))
hyperliquid_connector = importlib.util.module_from_spec(connector_spec)
connector_spec.loader.exec_module(hyperliquid_connector)

get_hyperliquid_connector = hyperliquid_connector.get_hyperliquid_connector
HyperliquidConnector = hyperliquid_connector.HyperliquidConnector

# Import strategy templates
ai_agent_dir = os.path.join(os.path.dirname(current_dir), "ai-agent")
strategy_spec = importlib.util.spec_from_file_location("strategy_templates", os.path.join(ai_agent_dir, "strategy_templates.py"))
strategy_templates = importlib.util.module_from_spec(strategy_spec)
strategy_spec.loader.exec_module(strategy_templates)

StrategyConfig = strategy_templates.StrategyConfig
StrategyType = strategy_templates.StrategyType

logger = logging.getLogger(__name__)

class MCPTradingServer:
    """MCP Server for trading operations"""
    
    def __init__(self):
        self.hyperliquid_connector: Optional[HyperliquidConnector] = None
        self.active_strategies: Dict[str, Dict[str, Any]] = {}
        self.backtest_results: Dict[str, Dict[str, Any]] = {}
        
    async def initialize(self):
        """Initialize the MCP server and connections"""
        self.hyperliquid_connector = await get_hyperliquid_connector()
        logger.info("MCP Trading Server initialized")
    
    async def profile_info(self, address: str) -> Dict[str, Any]:
        """
        Get trading profile information for an address
        
        Args:
            address: Wallet address to analyze
            
        Returns:
            Dict containing profile information
        """
        try:
            if not self.hyperliquid_connector:
                await self.initialize()
            
            user_state = await self.hyperliquid_connector.get_user_state(address)
            positions = await self.hyperliquid_connector.get_user_positions(address)
            recent_fills = await self.hyperliquid_connector.get_user_fills(address, limit=50)
            
            # Calculate basic metrics
            total_account_value = float(user_state.get("crossMarginSummary", {}).get("accountValue", "0"))
            total_margin_used = float(user_state.get("crossMarginSummary", {}).get("totalMarginUsed", "0"))
            
            leverage_ratio = (total_margin_used / total_account_value) if total_account_value > 0 else 0
            
            return {
                "address": address,
                "account_value": total_account_value,
                "margin_used": total_margin_used,
                "leverage_ratio": leverage_ratio,
                "active_positions": len(positions),
                "recent_trades": len(recent_fills),
                "positions": positions,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting profile info: {e}")
            return {"error": str(e)}
    
    async def generate_config(self, strategy_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate Hummingbot configuration from strategy template
        
        Args:
            strategy_config: Strategy configuration dictionary
            
        Returns:
            Generated Hummingbot configuration
        """
        try:
            strategy = StrategyConfig(**strategy_config)
            hummingbot_config = strategy.to_hummingbot_config()
            
            # Add additional Hummingbot-specific settings
            hummingbot_config.update({
                "exchange": "hyperliquid_perpetual",
                "kill_switch_enabled": True,
                "kill_switch_rate": -0.05,  # Kill switch at -5% portfolio loss
                "order_refresh_tolerance_pct": 0.002,
                "filled_order_delay": 60,
                "hanging_orders_enabled": False,
                "hanging_orders_cancel_pct": 0.1
            })
            
            return {
                "config_id": str(uuid.uuid4()),
                "strategy_name": strategy.name,
                "config": hummingbot_config,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating config: {e}")
            return {"error": str(e)}
    
    async def update_config(self, config_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing strategy configuration
        
        Args:
            config_id: Configuration ID to update
            updates: Dictionary of updates to apply
            
        Returns:
            Updated configuration
        """
        try:
            if config_id in self.active_strategies:
                current_config = self.active_strategies[config_id]["config"]
                current_config.update(updates)
                
                self.active_strategies[config_id]["updated_at"] = datetime.now().isoformat()
                self.active_strategies[config_id]["config"] = current_config
                
                return {
                    "config_id": config_id,
                    "status": "updated",
                    "config": current_config,
                    "updated_at": self.active_strategies[config_id]["updated_at"]
                }
            else:
                return {"error": f"Configuration {config_id} not found"}
                
        except Exception as e:
            logger.error(f"Error updating config: {e}")
            return {"error": str(e)}
    
    async def deploy_strategy(self, config_id: str) -> Dict[str, Any]:
        """
        Deploy a strategy configuration
        
        Args:
            config_id: Configuration ID to deploy
            
        Returns:
            Deployment status and details
        """
        try:
            if config_id not in self.active_strategies:
                return {"error": f"Configuration {config_id} not found"}
            
            strategy_info = self.active_strategies[config_id]
            
            # In a real implementation, this would integrate with Hummingbot V2
            # For now, we'll simulate deployment
            deployment_id = str(uuid.uuid4())
            
            strategy_info.update({
                "deployment_id": deployment_id,
                "status": "deployed",
                "deployed_at": datetime.now().isoformat()
            })
            
            return {
                "deployment_id": deployment_id,
                "config_id": config_id,
                "status": "deployed",
                "message": "Strategy deployed successfully",
                "deployed_at": strategy_info["deployed_at"]
            }
            
        except Exception as e:
            logger.error(f"Error deploying strategy: {e}")
            return {"error": str(e)}
    
    async def backtest_strategy(self, strategy_config: Dict[str, Any], 
                               start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Backtest a strategy configuration
        
        Args:
            strategy_config: Strategy configuration to test
            start_date: Start date for backtest (ISO format)
            end_date: End date for backtest (ISO format)
            
        Returns:
            Backtest results
        """
        try:
            backtest_id = str(uuid.uuid4())
            
            # Mock backtest results for demonstration
            # In real implementation, this would run actual backtesting
            mock_results = {
                "backtest_id": backtest_id,
                "strategy_name": strategy_config.get("name", "Unknown"),
                "period": f"{start_date} to {end_date}",
                "total_return": 0.15,  # 15% return
                "sharpe_ratio": 1.8,
                "max_drawdown": -0.08,  # -8% max drawdown
                "win_rate": 0.62,  # 62% win rate
                "total_trades": 145,
                "avg_trade_duration": "4.2 hours",
                "profit_factor": 1.45,
                "performance_chart": {
                    "dates": ["2024-01-01", "2024-01-15", "2024-01-30"],
                    "values": [10000, 10800, 11500]
                },
                "trades": [
                    {
                        "date": "2024-01-02",
                        "symbol": "BTC",
                        "side": "buy",
                        "pnl": 150.0,
                        "duration": "3.5 hours"
                    },
                    {
                        "date": "2024-01-03",
                        "symbol": "ETH",
                        "side": "sell",
                        "pnl": -80.0,
                        "duration": "2.1 hours"
                    }
                ],
                "backtested_at": datetime.now().isoformat()
            }
            
            self.backtest_results[backtest_id] = mock_results
            
            return mock_results
            
        except Exception as e:
            logger.error(f"Error running backtest: {e}")
            return {"error": str(e)}
    
    async def monitor_performance(self, deployment_id: str) -> Dict[str, Any]:
        """
        Monitor performance of a deployed strategy
        
        Args:
            deployment_id: Deployment ID to monitor
            
        Returns:
            Performance metrics and status
        """
        try:
            # Find strategy by deployment ID
            strategy_info = None
            for config_id, info in self.active_strategies.items():
                if info.get("deployment_id") == deployment_id:
                    strategy_info = info
                    break
            
            if not strategy_info:
                return {"error": f"Deployment {deployment_id} not found"}
            
            # Mock performance monitoring
            performance = {
                "deployment_id": deployment_id,
                "status": "running",
                "uptime": "2 days, 14 hours",
                "current_pnl": 245.80,
                "daily_pnl": 85.20,
                "trades_today": 12,
                "success_rate": 0.67,
                "current_positions": 2,
                "risk_metrics": {
                    "current_leverage": 3.2,
                    "margin_usage": 0.45,
                    "var_95": -150.0
                },
                "last_updated": datetime.now().isoformat()
            }
            
            return performance
            
        except Exception as e:
            logger.error(f"Error monitoring performance: {e}")
            return {"error": str(e)}
    
    async def risk_controls(self, deployment_id: str, 
                           risk_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update risk control parameters for a deployed strategy
        
        Args:
            deployment_id: Deployment ID to update
            risk_params: Risk control parameters
            
        Returns:
            Updated risk control status
        """
        try:
            # Find strategy by deployment ID
            strategy_info = None
            config_id = None
            for cid, info in self.active_strategies.items():
                if info.get("deployment_id") == deployment_id:
                    strategy_info = info
                    config_id = cid
                    break
            
            if not strategy_info:
                return {"error": f"Deployment {deployment_id} not found"}
            
            # Update risk controls
            if "risk_controls" not in strategy_info:
                strategy_info["risk_controls"] = {}
            
            strategy_info["risk_controls"].update(risk_params)
            strategy_info["risk_controls"]["updated_at"] = datetime.now().isoformat()
            
            return {
                "deployment_id": deployment_id,
                "risk_controls": strategy_info["risk_controls"],
                "status": "updated",
                "message": "Risk control parameters updated successfully"
            }
            
        except Exception as e:
            logger.error(f"Error updating risk controls: {e}")
            return {"error": str(e)}
    
    async def emergency_stop(self, deployment_id: str) -> Dict[str, Any]:
        """
        Emergency stop for a deployed strategy
        
        Args:
            deployment_id: Deployment ID to stop
            
        Returns:
            Stop status
        """
        try:
            # Find and stop strategy
            strategy_info = None
            for config_id, info in self.active_strategies.items():
                if info.get("deployment_id") == deployment_id:
                    strategy_info = info
                    break
            
            if not strategy_info:
                return {"error": f"Deployment {deployment_id} not found"}
            
            strategy_info["status"] = "stopped"
            strategy_info["stopped_at"] = datetime.now().isoformat()
            strategy_info["stop_reason"] = "emergency_stop"
            
            return {
                "deployment_id": deployment_id,
                "status": "stopped",
                "message": "Strategy emergency stopped successfully",
                "stopped_at": strategy_info["stopped_at"]
            }
            
        except Exception as e:
            logger.error(f"Error stopping strategy: {e}")
            return {"error": str(e)}
    
    async def get_market_data(self, symbols: List[str]) -> Dict[str, Any]:
        """
        Get current market data for specified symbols
        
        Args:
            symbols: List of symbols to get data for
            
        Returns:
            Market data for symbols
        """
        try:
            if not self.hyperliquid_connector:
                await self.initialize()
            
            market_info = await self.hyperliquid_connector.get_market_info()
            
            filtered_data = {}
            for symbol in symbols:
                if symbol in market_info.get("prices", {}):
                    filtered_data[symbol] = {
                        "price": market_info["prices"][symbol],
                        "timestamp": market_info["timestamp"]
                    }
            
            return {
                "symbols": filtered_data,
                "meta": market_info.get("meta", {}),
                "retrieved_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting market data: {e}")
            return {"error": str(e)}

# Global MCP server instance
mcp_server = MCPTradingServer()

# MCP Tool functions that can be called by Claude
async def mcp_profile_info(address: str) -> str:
    """Get trading profile information"""
    result = await mcp_server.profile_info(address)
    return json.dumps(result, indent=2)

async def mcp_generate_config(strategy_config: str) -> str:
    """Generate strategy configuration"""
    config_dict = json.loads(strategy_config)
    result = await mcp_server.generate_config(config_dict)
    return json.dumps(result, indent=2)

async def mcp_backtest_strategy(strategy_config: str, start_date: str, end_date: str) -> str:
    """Backtest a strategy"""
    config_dict = json.loads(strategy_config)
    result = await mcp_server.backtest_strategy(config_dict, start_date, end_date)
    return json.dumps(result, indent=2)

async def mcp_deploy_strategy(config_id: str) -> str:
    """Deploy a strategy"""
    result = await mcp_server.deploy_strategy(config_id)
    return json.dumps(result, indent=2)

async def mcp_monitor_performance(deployment_id: str) -> str:
    """Monitor strategy performance"""
    result = await mcp_server.monitor_performance(deployment_id)
    return json.dumps(result, indent=2)

# Initialize server on import
async def initialize_mcp_server():
    """Initialize the MCP server"""
    await mcp_server.initialize()

# Auto-initialize removed - will be called manually