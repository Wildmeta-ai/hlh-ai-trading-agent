import asyncio
import json
import logging
import os
import sys
import importlib.util
from typing import Dict, Any, List, Optional


# Import MCP server module
# Get backend directory path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
mcp_spec = importlib.util.spec_from_file_location(
    "mcp_server", os.path.join(backend_dir, "mcp-server/mcp_server.py"))
mcp_module = importlib.util.module_from_spec(mcp_spec)
mcp_spec.loader.exec_module(mcp_module)

# Import data analysis module
try:
    sys.path.append(backend_dir)
    from data import get_trader_analysis
except ImportError:
    def get_trader_analysis(*args, **kwargs):
        return {"error": "Data analysis module not available"}

# Import AI agent module


logger = logging.getLogger(__name__)


class ToolExecutor:
    """MCP Tool Executor"""

    def __init__(self):
        self.mcp_server = None
        self.mcp_initialized = False
        logger.info("Tool executor initialized")

    async def _initialize_mcp(self):
        """Initialize MCP server"""
        try:
            self.mcp_server = mcp_module.MCPTradingServer()
            await self.mcp_server.initialize()
            self.mcp_initialized = True
            logger.info("MCP server initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize MCP server: {e}")
            raise

    async def _ensure_mcp_initialized(self):
        """Ensure MCP server is initialized"""
        if not self.mcp_initialized:
            await self._initialize_mcp()

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools"""
        return [
            # {
            #     "name": "get_trader_analysis",
            #     "description": "Analyze trader performance and generate insights",
            #     "input_schema": {
            #         "type": "object",
            #         "properties": {
            #             "wallet_address": {"type": "string", "description": "Trader's wallet address"}
            #         },
            #         "required": ["wallet_address"]
            #     }
            # },
            # {
            #     "name": "generate_strategies",
            #     "description": "Generate trading strategies based on trader analysis and preferences",
            #     "input_schema": {
            #         "type": "object",
            #         "properties": {
            #             "trader_analysis": {"type": "object", "description": "Trader analysis data from get_trader_analysis"},
            #             "user_preferences": {"type": "object", "description": "User trading preferences and requirements"},
            #             "strategy_type": {"type": "string", "description": "Preferred strategy type (optional)", "enum": ["conservative_market_maker", "aggressive_scalper", "rsi_directional", "macd_trend"]}
            #         },
            #         "required": ["user_preferences"]
            #     }
            # },
            {
                "name": "backtest_strategy",
                "description": "Backtest a trading strategy",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "strategy_name": {"type": "string", "description": "Name of the strategy to backtest"},
                        "parameters": {"type": "object", "description": "Strategy parameters"},
                        "timeframe": {"type": "string", "description": "Backtest timeframe", "default": "30d"}
                    },
                    "required": ["strategy_name"]
                }
            },
            {
                "name": "profile_info",
                "description": "Get trader profile information",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "wallet_address": {"type": "string", "description": "Trader's wallet address"}
                    },
                    "required": ["wallet_address"]
                }
            }
        ]

    async def execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute specified tool"""
        try:
            await self._ensure_mcp_initialized()

            if tool_name == "get_trader_analysis":
                return await self._execute_trader_analysis(tool_input)
            elif tool_name == "generate_strategies":
                return await self._execute_generate_strategies(tool_input)
            elif tool_name == "backtest_strategy":
                return await self._execute_backtest_strategy(tool_input)
            elif tool_name == "profile_info":
                return await self._execute_profile_info(tool_input)
            else:
                return {
                    "success": False,
                    "error": f"Unknown tool: {tool_name}"
                }

        except Exception as e:
            logger.error(
                f"Tool execution error for {tool_name}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    async def _execute_trader_analysis(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute trader analysis"""
        wallet_address = tool_input.get("wallet_address")
        if not wallet_address:
            return {
                "success": False,
                "error": "wallet_address is required"
            }

        try:
            analysis_result = await get_trader_analysis(wallet_address)
            return {
                "success": True,
                "payload": analysis_result,
                "message": f"Analysis completed for wallet {wallet_address}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Analysis failed: {str(e)}"
            }

    async def _execute_generate_strategies(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute strategy generation"""
        user_preferences = tool_input.get("user_preferences")
        trader_analysis = tool_input.get("trader_analysis")
        strategy_type = tool_input.get("strategy_type")

        if not user_preferences:
            return {
                "success": False,
                "error": "user_preferences is required"
            }

        try:
            # Import strategy agent
            from .strategy_agent import StrategyAgent

            # Initialize strategy agent
            strategy_agent = StrategyAgent()

            # Generate strategies using strategy agent
            if trader_analysis:
                strategies = await strategy_agent.generate_strategies(
                    trader_analysis=trader_analysis,
                    user_preferences=user_preferences or {}
                )
            else:
                # If no trader analysis, create minimal analysis for strategy generation
                minimal_analysis = {
                    "ai_profile": {"trader": "general", "labels": []},
                    "technical_metrics": {},
                    "user_preferences": user_preferences or {}
                }
                strategies = await strategy_agent.generate_strategies(
                    trader_analysis=minimal_analysis,
                    user_preferences=user_preferences or {}
                )

            # Extract strategies from agent response
            strategy_list = strategies.get("strategies", [])

            return {
                "success": True,
                "payload": strategy_list,
                "message": f"Generated {len(strategy_list)} strategy configurations"
            }
        except Exception as e:
            logger.error(f"Strategy generation failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Strategy generation failed: {str(e)}"
            }

    async def _execute_backtest_strategy(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute strategy backtesting"""
        strategy_name = tool_input.get("strategy_name")
        parameters = tool_input.get("parameters", {})
        timeframe = tool_input.get("timeframe", "30d")

        if not strategy_name:
            return {
                "success": False,
                "error": "strategy_name is required"
            }

        try:
            # Call MCP server's backtesting functionality
            result = await self.mcp_server.backtest_strategy(
                strategy_name,
                parameters,
                timeframe
            )
            return {
                "success": True,
                "payload": result,
                "message": f"Backtest completed for {strategy_name}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Backtest failed: {str(e)}"
            }

    async def _execute_profile_info(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute user profile information retrieval"""
        wallet_address = tool_input.get("wallet_address")
        if not wallet_address:
            return {
                "success": False,
                "error": "wallet_address is required"
            }

        try:
            # Call MCP server's profile information functionality
            result = await self.mcp_server.get_profile_info(wallet_address)
            return {
                "success": True,
                "payload": result,
                "message": f"Profile info retrieved for {wallet_address}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Profile info retrieval failed: {str(e)}"
            }
