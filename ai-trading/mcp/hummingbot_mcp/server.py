"""
Main MCP server for Hummingbot API integration
"""

import asyncio
import logging
import sys
import os
import ssl
from typing import Any, Literal, Optional, Dict, List
import aiohttp
import json

from fastmcp import FastMCP

from hummingbot_mcp.exceptions import MaxConnectionsAttemptError as HBConnectionError, ToolError
from hummingbot_mcp.hummingbot_client import hummingbot_client
from hummingbot_mcp.settings import settings
from hummingbot_mcp.tools.account import SetupConnectorRequest

# Configure root logger
logging.basicConfig(
    level="INFO",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger("hummingbot-mcp")

# Initialize FastMCP server
mcp = FastMCP("hummingbot-mcp")


# Account Management Tools


# @mcp.tool()
# async def setup_connector(
#         connector: str | None = None,
#         credentials: dict[str, Any] | None = None,
#         account: str | None = None,
#         confirm_override: bool | None = None,
# ) -> str:
#     """Setup a new exchange connector for an account with credentials using progressive disclosure.

#     This tool guides you through the entire process of connecting an exchange with a four-step flow:
#     1. No parameters → List available exchanges
#     2. Connector only → Show required credential fields
#     3. Connector + credentials, no account → Select account from available accounts
#     4. All parameters → Connect the exchange (with override confirmation if needed)

#     Args:
#         connector: Exchange connector name (e.g., 'binance', 'binance_perpetual'). Leave empty to list available connectors.
#         credentials: Credentials object with required fields for the connector. Leave empty to see required fields first.
#         account: Account name to add credentials to. If not provided, prompts for account selection.
#         confirm_override: Explicit confirmation to override existing connector. Required when connector already exists.
#     """
#     try:
#         # Create and validate request using Pydantic model
#         request = SetupConnectorRequest(
#             connector=connector, credentials=credentials, account=account, confirm_override=confirm_override
#         )

#         from .tools.account import setup_connector as setup_connector_impl

#         result = await setup_connector_impl(request)
#         return f"Setup Connector Result: {result}"
#     except Exception as e:
#         logger.error(f"setup_connector failed: {str(e)}", exc_info=True)
#         raise ToolError(f"Failed to setup connector: {str(e)}")


# @mcp.tool()
# async def get_portfolio_balances(
#         account_names: list[str] | None = None, connector_names: list[str] | None = None, as_distribution: bool = False
# ) -> str:
#     """Get portfolio balances and holdings across all connected exchanges.

#     Returns detailed token balances, values, and available units for each account. Use this to check your portfolio,
#     see what tokens you hold, and their current values. If passing accounts and connectors it will only return the
#     filtered accounts and connectors, leave it empty to return all accounts and connectors.
#     You can also get the portfolio distribution by setting `as_distribution` to True, which will return the distribution
#     of tokens and their values across accounts and connectors and the percentage of each token in the portfolio.

#     Args:
#         account_names: List of account names to filter by (optional). If empty, returns all accounts.
#         connector_names: List of connector names to filter by (optional). If empty, returns all connectors.
#         as_distribution: If True, returns the portfolio distribution as a percentage of each token in the portfolio and
#         their values across accounts and connectors. Defaults to False.
#     """
#     try:
#         # Get account credentials to know which exchanges are connected
#         client = await hummingbot_client.get_client()
#         if as_distribution:
#             # Get portfolio distribution
#             result = await client.portfolio.get_distribution(account_names=account_names,
#                                                              connector_names=connector_names)
#             return f"Portfolio Distribution: {result}"
#         account_info = await client.portfolio.get_state(account_names=account_names, connector_names=connector_names)
#         return f"Account State: {account_info}"
#     except Exception as e:
#         logger.error(f"get_account_state failed: {str(e)}", exc_info=True)
#         raise ToolError(f"Failed to get account state: {str(e)}")


# # Trading Tools


# @mcp.tool()
# async def place_order(
#         connector_name: str,
#         trading_pair: str,
#         trade_type: str,
#         amount: str,
#         price: str | None = None,
#         order_type: str = "MARKET",
#         position_action: str | None = "OPEN",
#         account_name: str | None = "master_account",
# ) -> str:
#     """Place a buy or sell order (supports USD values by adding at the start of the amount $).

#     Args:
#         connector_name: Exchange connector name (e.g., 'binance', 'binance_perpetual')
#         trading_pair: Trading pair (e.g., BTC-USDT, ETH-USD)
#         trade_type: Order side ('BUY' or 'SELL')
#         amount: Order amount (is always in base currency, if you want to use USD values, add a dollar sign at the start, e.g., '$100')
#         order_type: Order type ('MARKET' or 'LIMIT')
#         price: Price for limit orders (required for limit orders)
#         position_action: Position action ('OPEN', 'CLOSE'). Defaults to 'OPEN' and is useful for perpetuals with HEDGE mode where you
#         can hold a long and short position at the same time.
#         account_name: Account name (default: master_account)
#     """
#     client = await hummingbot_client.get_client()
#     try:
#         if "$" in str(amount) and price is None:
#             prices = await client.market_data.get_prices(connector_name=connector_name, trading_pairs=trading_pair)
#             price_value = float(prices["prices"][trading_pair])
#             amount_value = float(str(amount).replace("$", "")) / price_value
#         else:
#             amount_value = float(amount)
#         result = await client.trading.place_order(
#             account_name=account_name,
#             connector_name=connector_name,
#             trading_pair=trading_pair,
#             trade_type=trade_type,
#             amount=amount_value,
#             order_type=order_type,
#             price=price,
#             position_action=position_action,
#         )
#         return f"Order Result: {result}"
#     except Exception as e:
#         logger.error(f"place_order failed: {str(e)}", exc_info=True)
#         raise ToolError(f"Failed to place order: {str(e)}")


# @mcp.tool()
# async def set_account_position_mode_and_leverage(
#         account_name: str,
#         connector_name: str,
#         trading_pair: str | None = None,
#         position_mode: str | None = None,
#         leverage: int | None = None,
# ) -> str:
#     """Set position mode and leverage for an account on a specific exchange. If position mode is not specified, will only
#     set the leverage. If leverage is not specified, will only set the position mode.

#     Args:
#         account_name: Account name (default: master_account)
#         connector_name: Exchange connector name (e.g., 'binance_perpetual')
#         trading_pair: Trading pair (e.g., ETH-USD) only required for setting leverage
#         position_mode: Position mode ('HEDGE' or 'ONE-WAY')
#         leverage: Leverage to set (optional, required for HEDGE mode)
#     """

#     try:
#         client = await hummingbot_client.get_client()
#         if position_mode is None and leverage is None:
#             raise ValueError("At least one of position_mode or leverage must be specified")
#         response = ""
#         if position_mode:
#             position_mode = position_mode.upper()
#             if position_mode not in ["HEDGE", "ONE-WAY"]:
#                 raise ValueError("Invalid position mode. Must be 'HEDGE' or 'ONE-WAY'")
#             position_mode_result = await client.trading.set_position_mode(
#                 account_name=account_name, connector_name=connector_name, position_mode=position_mode
#             )
#             response += f"Position Mode Set: {position_mode_result}\n"
#         if leverage is not None:
#             if not isinstance(leverage, int) or leverage <= 0:
#                 raise ValueError("Leverage must be a positive integer")
#             if trading_pair is None:
#                 raise ValueError("Trading_pair must be specified")
#             leverage_result = await client.trading.set_leverage(
#                 account_name=account_name, connector_name=connector_name, trading_pair=trading_pair, leverage=leverage
#             )
#             response += f"Leverage Set: {leverage_result}\n"
#         return f"{response.strip()}"
#     except Exception as e:
#         logger.error(f"set_account_position_mode_and_leverage failed: {str(e)}", exc_info=True)
#         raise ToolError(f"Failed to set position mode and leverage: {str(e)}")


# @mcp.tool()
# async def get_orders(
#         account_names: list[str] | None = None,
#         connector_names: list[str] | None = None,
#         trading_pairs: list[str] | None = None,
#         status: Literal["OPEN", "FILLED", "CANCELED", "FAILED"] | None = None,
#         start_time: int | None = None,
#         end_time: int | None = None,
#         limit: int | None = 500,
#         cursor: str | None = None,
# ) -> str:
#     """Get the orders manged by the connected accounts.

#     Args:
#         account_names: List of account names to filter by (optional). If empty, returns all accounts.
#         connector_names: List of connector names to filter by (optional). If empty, returns all connectors.
#         trading_pairs: List of trading pairs to filter by (optional). If empty, returns all trading pairs.
#         status: Order status to filter by can be OPEN, PARTIALLY_FILLED, FILLED, CANCELED, FAILED (is optional).
#         start_time: Start time (in seconds) to filter by (optional).
#         end_time: End time (in seconds) to filter by (optional).
#         limit: Number of orders to return defaults to 500, maximum is 1000.
#         cursor: Cursor for pagination (optional, should be used if another request returned a cursor).
#     """

#     try:
#         client = await hummingbot_client.get_client()
#         result = await client.trading.search_orders(
#             account_names=account_names,
#             connector_names=connector_names,
#             trading_pairs=trading_pairs,
#             status=status,
#             start_time=start_time,
#             end_time=end_time,
#             limit=limit,
#             cursor=cursor,
#         )
#         return f"Order Management Result: {result}"
#     except Exception as e:
#         logger.error(f"manage_orders failed: {str(e)}", exc_info=True)
#         raise ToolError(f"Failed to manage orders: {str(e)}")


# @mcp.tool()
# async def get_positions(
#         account_names: list[str] | None = None, connector_names: list[str] | None = None, limit: int | None = 100
# ) -> str:
#     """Get the positions managed by the connected accounts.

#     Args:
#         account_names: List of account names to filter by (optional). If empty, returns all accounts.
#         connector_names: List of connector names to filter by (optional). If empty, returns all connectors.
#         limit: Number of positions to return defaults to 100, maximum is 1000.
#     """
#     try:
#         client = await hummingbot_client.get_client()
#         result = await client.trading.get_positions(account_names=account_names, connector_names=connector_names,
#                                                     limit=limit)
#         return f"Position Management Result: {result}"
#     except Exception as e:
#         logger.error(f"manage_positions failed: {str(e)}", exc_info=True)
#         raise ToolError(f"Failed to manage positions: {str(e)}")


# # Market Data Tools


# @mcp.tool()
# async def get_prices(connector_name: str, trading_pairs: list[str]) -> str:
#     """Get the latest prices for the specified trading pairs on a specific exchange connector.
#     Args:
#         connector_name: Exchange connector name (e.g., 'binance', 'binance_perpetual')
#         trading_pairs: List of trading pairs to get prices for (e.g., ['BTC-USDT', 'ETH-USD'])
#     """
#     try:
#         client = await hummingbot_client.get_client()
#         prices = await client.market_data.get_prices(connector_name=connector_name, trading_pairs=trading_pairs)
#         return f"Price results: {prices}"
#     except Exception as e:
#         logger.error(f"get_prices failed: {str(e)}", exc_info=True)
#         raise ToolError(f"Failed to get prices: {str(e)}")


# @mcp.tool()
# async def get_candles(connector_name: str, trading_pair: str, interval: str = "1h", days: int = 30) -> str:
#     """Get the real-time candles for a trading pair on a specific exchange connector.
#     Args:
#         connector_name: Exchange connector name (e.g., 'binance', 'binance_perpetual')
#         trading_pair: Trading pair to get candles for (e.g., 'BTC-USDT')
#         interval: Candle interval (default: '1h'). Options include '1m', '5m', '15m', '30m', '1h', '4h', '1d'.
#         days: Number of days of historical data to retrieve (default: 30).
#     """
#     try:
#         client = await hummingbot_client.get_client()
#         available_candles_connectors = await client.market_data.get_available_candle_connectors()
#         if connector_name not in available_candles_connectors:
#             raise ValueError(
#                 f"Connector '{connector_name}' does not support candle data. Available connectors: {available_candles_connectors}"
#             )
#         # Determine max records based on interval "m" is minute, "s" is second, "h" is hour, "d" is day, "w" is week
#         if interval.endswith("m"):
#             max_records = 1440 * days  # 1440 minutes in a day
#         elif interval.endswith("h"):
#             max_records = 24 * days
#         elif interval.endswith("d"):
#             max_records = days
#         elif interval.endswith("w"):
#             max_records = 7 * days
#         else:
#             raise ValueError(
#                 f"Unsupported interval format: {interval}. Use '1m', '5m', '15m', '30m', '1h', '4h', '1d', or '1w'.")
#         max_records = int(max_records / int(interval[:-1])) if interval[:-1] else max_records

#         candles = await client.market_data.get_candles(
#             connector_name=connector_name, trading_pair=trading_pair, interval=interval, max_records=max_records
#         )
#         return f"Candle results: {candles}"
#     except Exception as e:
#         logger.error(f"get_candles failed: {str(e)}", exc_info=True)
#         raise ToolError(f"Failed to get candles: {str(e)}")


# @mcp.tool()
# async def get_funding_rate(connector_name: str, trading_pair: str) -> str:
#     """Get the latest funding rate for a trading pair on a specific exchange connector. Only works for perpetual
#     connectors so the connector name must have _perpetual in it.
#     Args:
#         connector_name: Exchange connector name (e.g., 'binance_perpetual', 'hyperliquid_perpetual')
#         trading_pair: Trading pair to get funding rate for (e.g., 'BTC-USDT')
#     """
#     try:
#         client = await hummingbot_client.get_client()
#         if "_perpetual" not in connector_name:
#             raise ValueError(
#                 f"Connector '{connector_name}' is not a perpetual connector. Funding rates are only available for"
#                 f"perpetual connectors."
#             )
#         funding_rate = await client.market_data.get_funding_info(connector_name=connector_name,
#                                                                  trading_pair=trading_pair)
#         return f"Funding Rate: {funding_rate}"
#     except Exception as e:
#         logger.error(f"get_funding_rate failed: {str(e)}", exc_info=True)
#         raise ToolError(f"Failed to get funding rate: {str(e)}")


# @mcp.tool()
# async def get_order_book(
#         connector_name: str,
#         trading_pair: str,
#         query_type: Literal[
#             "snapshot", "volume_for_price", "price_for_volume", "quote_volume_for_price", "price_for_quote_volume"],
#         query_value: float | None = None,
#         is_buy: bool = True,
# ) -> str:
#     """Get order book data for a trading pair on a specific exchange connector, if the query type is different than
#     snapshot, you need to provide query_value and is_buy
#     Args:
#         connector_name: Connector name (e.g., 'binance', 'binance_perpetual')
#         trading_pair: Trading pair (e.g., BTC-USDT)
#         query_type: Order book query type ('snapshot', 'volume_for_price', 'price_for_volume', 'quote_volume_for_price',
#         'price_for_quote_volume')
#         query_value: Only required if query_type is not 'snapshot'. The value to query against the order book.
#         is_buy: Only required if query_type is not 'snapshot'. Is important to see what orders of the book analyze.
#     """
#     try:
#         client = await hummingbot_client.get_client()
#         if query_type == "snapshot":
#             order_book = await client.market_data.get_order_book(connector_name=connector_name,
#                                                                  trading_pair=trading_pair)
#             return f"Order Book Snapshot: {order_book}"
#         else:
#             if query_value is None:
#                 raise ValueError(f"query_value must be provided for query_type '{query_type}'")
#             if query_type == "volume_for_price":
#                 result = await client.market_data.get_volume_for_price(
#                     connector_name=connector_name, trading_pair=trading_pair, price=query_value, is_buy=is_buy
#                 )
#             elif query_type == "price_for_volume":
#                 result = await client.market_data.get_price_for_volume(
#                     connector_name=connector_name, trading_pair=trading_pair, volume=query_value, is_buy=is_buy
#                 )
#             elif query_type == "quote_volume_for_price":
#                 result = await client.market_data.get_quote_volume_for_price(
#                     connector_name=connector_name, trading_pair=trading_pair, price=query_value, is_buy=is_buy
#                 )
#             elif query_type == "price_for_quote_volume":
#                 result = await client.market_data.get_price_for_quote_volume(
#                     connector_name=connector_name, trading_pair=trading_pair, quote_volume=query_value, is_buy=is_buy
#                 )
#             else:
#                 raise ValueError(f"Unsupported query type: {query_type}")
#             return f"Order Book Query Result: {result}"
#     except Exception as e:
#         logger.error(f"get_market_data failed: {str(e)}", exc_info=True)
#         raise ToolError(f"Failed to get market data: {str(e)}")

# # Weather Tools


# @mcp.tool()
# async def get_weather(
#         city: str,
#         country: str | None = None,
#         units: Literal["celsius", "fahrenheit"] = "celsius"
# ) -> str:
#     """Get current weather information for a specified city (mock data).
    
#     This is a mock weather tool that returns simulated weather data for demonstration purposes.
    
#     Args:
#         city: Name of the city to get weather for (e.g., 'Beijing', 'New York')
#         country: Country code or name (optional, e.g., 'CN', 'US', 'China', 'United States')
#         units: Temperature units ('celsius' or 'fahrenheit'). Defaults to 'celsius'.
#     """
#     try:
#         import random
#         from datetime import datetime
        
#         # Mock weather data
#         weather_conditions = ["sunny", "cloudy", "partly cloudy", "rainy", "overcast"]
#         condition = random.choice(weather_conditions)
        
#         # Generate mock temperature based on units
#         if units == "celsius":
#             temperature = random.randint(-10, 35)
#             temp_unit = "°C"
#         else:
#             temperature = random.randint(14, 95)
#             temp_unit = "°F"
        
#         humidity = random.randint(30, 90)
#         wind_speed = random.randint(0, 25)
        
#         # Format location
#         location = f"{city}"
#         if country:
#             location += f", {country}"
        
#         # Create mock weather response
#         weather_data = {
#             "location": location,
#             "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
#             "condition": condition,
#             "temperature": f"{temperature}{temp_unit}",
#             "humidity": f"{humidity}%",
#             "wind_speed": f"{wind_speed} km/h",
#             "note": "This is mock weather data for demonstration purposes"
#         }
        
#         return f"Weather Information: {weather_data}"
#     except Exception as e:
#         logger.error(f"get_weather failed: {str(e)}", exc_info=True)
#         raise ToolError(f"Failed to get weather information: {str(e)}")


# @mcp.tool()
# async def explore_controllers(
#         action: Literal["list", "describe"],
#         controller_type: Literal["directional_trading", "market_making", "generic"] | None = None,
#         controller_name: str | None = None,
#         config_name: str | None = None,
# ) -> str:
#     """
#     Explore and understand controllers and their configs.
    
#     Use this tool to discover what's available and understand how things work.
    
#     Progressive flow:
#     1. action="list" → List all controllers and their configs
#     2. action="list" + controller_type → List controllers of that type with config counts
#     3. action="describe" + controller_name → Show controller code + list its configs + explain parameters
#     4. action="describe" + config_name → Show specific config details + which controller it uses

#     Common Enum Values for Controller Configs:
    
#     Position Mode (position_mode):
#     - "HEDGE" - Allows holding both long and short positions simultaneously
#     - "ONEWAY" - Allows only one direction position at a time
#     - Note: Use as string value, e.g., position_mode: "HEDGE"
    
#     Trade Side (side):
#     - 1 or "BUY" - For long/buy positions
#     - 2 or "SELL" - For short/sell positions  
#     - 3 - Other trade types
#     - Note: Numeric values are required for controller configs
    
#     Order Type (order_type, open_order_type, take_profit_order_type, etc.):
#     - 1 or "MARKET" - Market order
#     - 2 or "LIMIT" - Limit order
#     - 3 or "LIMIT_MAKER" - Limit maker order (post-only)
#     - 4 - Other order types
#     - Note: Numeric values are required for controller configs

#     Args:
#         action: "list" to list controllers or "describe" to show details of a specific controller or config.
#         controller_type: Type of controller to filter by (optional, e.g., 'directional_trading', 'market_making', 'generic').
#         controller_name: Name of the controller to describe (optional, only required for describe specific controller).
#         config_name: Name of the config to describe (optional, only required for describe specific config).
#     """
#     try:
#         client = await hummingbot_client.get_client()
#         # List all controllers and their configs
#         controllers = await client.controllers.list_controllers()
#         configs = await client.controllers.list_controller_configs()
#         result = ""
#         if action == "list":
#             result = "Available Controllers:\n\n"
#             for c_type, controllers in controllers.items():
#                 if controller_type is not None and c_type != controller_type:
#                     continue
#                 result += f"Controller Type: {c_type}\n"
#                 for controller in controllers:
#                     controller_configs = [c for c in configs if c.get('controller_name') == controller]
#                     result += f"- {controller} ({len(controller_configs)} configs)\n"
#                     if len(controller_configs) > 0:
#                         for config in controller_configs:
#                             result += f"    - {config.get('id', 'unknown')}\n"
#             return result
#         elif action == "describe":
#             config = await client.controllers.get_controller_config(config_name) if config_name else None
#             if config:
#                 if controller_name != config.get("controller_name"):
#                     controller_name = config.get("controller_name")
#                     result += f"Controller name not matching, using config's controller name: {controller_name}\n"
#                 result += f"Config Details for {config_name}:\n{config}\n\n"
#             if not controller_name:
#                 return "Please provide a controller name to describe."
#             # First, determine the controller type
#             controller_type = None
#             for c_type, controllers in controllers.items():
#                 if controller_name in controllers:
#                     controller_type = c_type
#                     break
#             if not controller_type:
#                 return f"Controller '{controller_name}' not found."
#             # Get controller code and configs
#             controller_code = await client.controllers.get_controller(controller_type, controller_name)
#             controller_configs = [c.get("id") for c in configs if c.get('controller_name') == controller_name]
#             result = f"Controller Code for {controller_name} ({controller_type}):\n{controller_code}\n\n"
#             template = await client.controllers.get_controller_config_template(controller_type, controller_name)
#             result += f"All configs available for controller:\n {controller_configs}"
#             result += f"\n\nController Config Template:\n{template}\n\n"
#             return result
#         else:
#             return "Invalid action. Use 'list' or 'describe', or omit for overview."
            
#     except HBConnectionError as e:
#         logger.error(f"Failed to connect to Hummingbot API: {e}")
#         raise ToolError(
#             "Failed to connect to Hummingbot API. Please ensure it is running and API credentials are correct.")


# @mcp.tool()
# async def modify_controllers(
#         action: Literal["upsert", "delete"],
#         target: Literal["controller", "config"],
#         # For controllers
#         controller_type: Literal["directional_trading", "market_making", "generic"] | None = None,
#         controller_name: str | None = None,
#         controller_code: str | None = None,
#         # For configs
#         config_name: str | None = None,
#         config_data: dict[str, Any] | None = None,
#         # For configs in bots
#         bot_name: str | None = None,
#         # Safety
#         confirm_override: bool = False,
# ) -> str:
#     """
#     Create, update, or delete controllers and their configurations. If bot name is provided, it can only modify the config
#     in the bot deployed with that name.
    
#     IMPORTANT: When creating a config without specifying config_data details, you MUST first use the explore_controllers tool
#     with action="describe" and the controller_name to understand what parameters are required. The config_data must include
#     ALL relevant parameters for the controller to function properly.
    
#     Controllers = are essentially strategies that can be run in Hummingbot.
#     Configs = are the parameters that the controller uses to run.

#     Args:
#         action: "upsert" (create/update) or "delete"
#         target: "controller" (template) or "config" (instance)
#         confirm_override: Required True if overwriting existing
#         config_data: For config creation, MUST contain all required controller parameters. Use explore_controllers first!
        
#     Workflow for creating a config:
#     1. Use explore_controllers(action="describe", controller_name="<name>") to see required parameters
#     2. Create config_data dict with ALL required parameters from the controller template
#     3. Call modify_controllers with the complete config_data
        
#     Examples:
#     - Create new controller: modify_controllers("upsert", "controller", controller_type="market_making", ...)
#     - Create config: modify_controllers("upsert", "config", config_name="pmm_btc", config_data={...})
#     - Modify config from bot: modify_controllers("upsert", "config", config_name="pmm_btc", config_data={...}, bot_name="my_bot")
#     - Delete config: modify_controllers("delete", "config", config_name="old_strategy")
#     """
#     try:
#         print(f"modify_controllers action: {action}, target: {target}, controller_type: {controller_type}, controller_name: {controller_name}, config_name: {config_name}, config_data: {config_data}, bot_name: {bot_name}, confirm_override: {confirm_override}")
#         client = await hummingbot_client.get_client()
        
#         if target == "controller":
#             if action == "upsert":
#                 if not controller_type or not controller_name or not controller_code:
#                     raise ValueError("controller_type, controller_name, and controller_code are required for controller upsert")
                
#                 # Check if controller exists
#                 controllers = await client.controllers.list_controllers()
#                 exists = controller_name in controllers.get(controller_type, [])
                
#                 if exists and not confirm_override:
#                     controller_code = await client.controllers.get_controller(controller_type, controller_name)
#                     return (f"Controller '{controller_name}' already exists and this is the current code: {controller_code}. "
#                             f"Set confirm_override=True to update it.")
                
#                 result = await client.controllers.create_or_update_controller(
#                     controller_type, controller_name, controller_code
#                 )
#                 return f"Controller {'updated' if exists else 'created'}: {result}"
                
#             elif action == "delete":
#                 if not controller_type or not controller_name:
#                     raise ValueError("controller_type and controller_name are required for controller delete")
                    
#                 result = await client.controllers.delete_controller(controller_type, controller_name)
#                 return f"Controller deleted: {result}"
                
#         elif target == "config":
#             if action == "upsert":
#                 if not config_name or not config_data:
#                     raise ValueError("config_name and config_data are required for config upsert")

#                 # Extract controller_type and controller_name from config_data
#                 config_controller_type = config_data.get("controller_type")
#                 config_controller_name = config_data.get("controller_name")
                
#                 if not config_controller_type or not config_controller_name:
#                     raise ValueError("config_data must include 'controller_type' and 'controller_name'")

#                 # validate config first
#                 await client.controllers.validate_controller_config(config_controller_type, config_controller_name, config_data)

#                 if bot_name:
#                     if not confirm_override:
#                         current_configs = await client.controllers.get_bot_controller_configs(bot_name)
#                         config = next((c for c in current_configs if c.get("id") == config_name), None)
#                         if config:
#                             return (f"Config '{config_name}' already exists in bot '{bot_name}' with data: {config}. "
#                                     "Set confirm_override=True to update it.")
#                         else:
#                             update_op = await client.controllers.create_or_update_bot_controller_config(config_name, config_data)
#                             return f"Config created in bot '{bot_name}': {update_op}"
#                     else:
#                         # Ensure config_data has the correct id
#                         if "id" not in config_data or config_data["id"] != config_name:
#                             config_data["id"] = config_name
#                         update_op = await client.controllers.create_or_update_bot_controller_config(config_name, config_data)
#                         return f"Config updated in bot '{bot_name}': {update_op}"
#                 else:
#                     # Ensure config_data has the correct id
#                     if "id" not in config_data or config_data["id"] != config_name:
#                         config_data["id"] = config_name

#                     controller_configs = await client.controllers.list_controller_configs()
#                     exists = config_name in controller_configs

#                     if exists and not confirm_override:
#                         existing_config = await client.controllers.get_controller_config(config_name)
#                         return (f"Config '{config_name}' already exists with data: {existing_config}."
#                                 "Set confirm_override=True to update it.")

#                     result = await client.controllers.create_or_update_controller_config(config_name, config_data)
#                     return f"Config {'updated' if exists else 'created'}: {result}"
                
#             elif action == "delete":
#                 if not config_name:
#                     raise ValueError("config_name is required for config delete")
                    
#                 result = await client.controllers.delete_controller_config(config_name)
#                 await client.bot_orchestration.deploy_v2_controllers()
#                 return f"Config deleted: {result}"
#         else:
#             raise ValueError("Invalid target. Must be 'controller' or 'config'.")
            
#     except HBConnectionError as e:
#         logger.error(f"Failed to connect to Hummingbot API: {e}")
#         raise ToolError(
#             "Failed to connect to Hummingbot API. Please ensure it is running and API credentials are correct.")
#     except Exception as e:
#         logger.error(f"Failed request to Hummingbot API: {e}")
#         raise ToolError(f"Failed to modify controllers/configs: {str(e)}")


# @mcp.tool()
# async def deploy_bot_with_controllers(
#         bot_name: str,
#         controllers_config: list[str],
#         account_name: str | None = "master_account",
#         max_global_drawdown_quote: float | None = None,
#         max_controller_drawdown_quote: float | None = None,
#         image: str = "hummingbot/hummingbot:latest",
# ) -> str:
#     """Deploy a bot with specified controller configurations.
#     Args:
#         bot_name: Name of the bot to deploy
#         controllers_config: List of controller configs to use for the bot deployment.
#         account_name: Account name to use for the bot (default: master_account)
#         max_global_drawdown_quote: Maximum global drawdown in quote currency (optional) defaults to None.
#         max_controller_drawdown_quote: Maximum drawdown per controller in quote currency (optional) defaults to None.
#         image: Docker image to use for the bot (default: "hummingbot/hummingbot:latest")
#     """
#     print(f"Deploying bot {bot_name} with controllers {controllers_config}")
#     try:
#         client = await hummingbot_client.get_client()
        
#         # CRITICAL: Validate that all controller configs exist before deployment
#         for config_name in controllers_config:
#             try:
#                 # Check if config exists by trying to get it
#                 configs = await client.controllers.list_controller_configs()
                
#                 # Handle both list of dicts and dict formats
#                 config_exists = False
#                 if isinstance(configs, list):
#                     # configs is a list of config dictionaries
#                     config_exists = any(config.get('id') == config_name for config in configs)
#                     available_config_names = [config.get('id', 'unknown') for config in configs]
#                 else:
#                     # configs is a dictionary
#                     config_exists = config_name in configs
#                     available_config_names = list(configs.keys())
                
#                 if not config_exists:
#                     raise ToolError(
#                         f"Controller config '{config_name}' does not exist. "
#                         f"You MUST create the config using modify_controllers before deploying. "
#                         f"Available configs: {available_config_names}"
#                     )
#             except Exception as e:
#                 raise ToolError(
#                     f"Failed to validate controller config '{config_name}': {str(e)}. "
#                     f"You MUST create configs using modify_controllers before deploying."
#                 )
        
#         # Validate controller configs
#         result = await client.bot_orchestration.deploy_v2_controllers(
#             instance_name=bot_name,
#             controllers_config=controllers_config,
#             credentials_profile=account_name,
#             max_global_drawdown_quote=max_global_drawdown_quote,
#             max_controller_drawdown_quote=max_controller_drawdown_quote,
#             image=image,
#         )
#         return f"Bot Deployment Result: {result}"
#     except HBConnectionError as e:
#         logger.error(f"Failed to connect to Hummingbot API: {e}")
#         raise ToolError(
#             "Failed to connect to Hummingbot API. Please ensure it is running and API credentials are correct.")


# @mcp.tool()
# async def get_active_bots_status():
#     """
#     Get the status of all active bots. Including the unrealized PnL, realized PnL, volume traded, latest logs, etc.
#     """
#     try:
#         client = await hummingbot_client.get_client()
#         active_bots = await client.bot_orchestration.get_active_bots_status()
#         return f"Active Bots Status: {active_bots}"
#     except HBConnectionError as e:
#         logger.error(f"Failed to connect to Hummingbot API: {e}")
#         raise ToolError(
#             "Failed to connect to Hummingbot API. Please ensure it is running and API credentials are correct.")


# @mcp.tool()
# async def stop_bot_or_controllers(
#         bot_name: str,
#         controller_names: Optional[list[str]] = None,
# ):
#     """
#     Stop and archive a bot forever or stop the execution of a controller of a runnning bot. If the controllers to stop
#     are not specified, it will stop the bot execution and archive it forever, if they are specified, will only stop
#     the execution of those controllers and the bot will still be running with the rest of the controllers.
#     Args:
#         bot_name: Name of the bot to stop
#         controller_names: List of controller names to stop (optional, if not provided will stop the bot execution)
#     """
#     try:
#         client = await hummingbot_client.get_client()
#         if controller_names is None or len(controller_names) == 0:
#             result = await client.bot_orchestration.stop_and_archive_bot(bot_name)
#             return f"Bot execution stopped and archived: {result}"
#         else:
#             tasks = [client.controllers.update_bot_controller_config(bot_name, controller, {"manual_kill_switch": True})
#                      for controller in controller_names]
#             result = await asyncio.gather(*tasks)
#             return f"Controller execution stopped: {result}"
#     except HBConnectionError as e:
#         logger.error(f"Failed to connect to Hummingbot API: {e}")
#         raise ToolError(
#             "Failed to connect to Hummingbot API. Please ensure it is running and API credentials are correct.")


# Trader Analysis Tools


@mcp.tool()
async def get_trader_analysis(
    wallet_address: str
) -> str:
    """Analyze trader performance and generate insights.
    
    Args:
        wallet_address: Trader's wallet address to analyze
    """
    try:
        logger.info(f"get_trader_analysis: {wallet_address}")
        if not wallet_address:
            raise ToolError("wallet_address is required")
        
        # Call the API server endpoint directly
        async with aiohttp.ClientSession() as session:
            api_url = f"{settings.backend_api_base_url}/trader-analysis"
            payload = {"address": wallet_address}
            
            async with session.post(api_url, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    analysis_result = result.get("analysis", {})
                    logger.info(f"get_trader_analysis done: {wallet_address}")
                    return f"Trader Analysis Result: {analysis_result}"
                else:
                    error_text = await response.text()
                    logger.info(f"get_trader_analysis done: {wallet_address} with error: {error_text}")
                    return f"Analysis failed: API returned status {response.status}: {error_text}"
        
    except Exception as e:
        logger.error(f"get_trader_analysis failed: {str(e)}", exc_info=True)
        raise ToolError(f"Failed to analyze trader: {str(e)}")


# generate_strategies function has been removed - strategy generation logic moved to coordinator agent


@mcp.tool()
async def run_backtesting(
    start_time: int,
    end_time: int,
    backtesting_resolution: str,
    trade_cost: float,
    config: dict[str, Any]
) -> str:
    """Run backtesting via external API endpoint.
    
    Args:
        start_time: Start time timestamp for backtesting
        end_time: End time timestamp for backtesting
        backtesting_resolution: Resolution for backtesting (e.g., '5m', '1h')
        trade_cost: Trading cost percentage (e.g., 0.0025 for 0.25%)
        config: Backtesting configuration including controller settings
    """
    try:
        logger.info(f"run_backtesting: start_time={start_time}, end_time={end_time}, resolution={backtesting_resolution}, trade_cost={trade_cost}")
        
        # Call the API server endpoint directly with timeout
        timeout = aiohttp.ClientTimeout(total=120)  # 120 second timeout for backtesting
        async with aiohttp.ClientSession(timeout=timeout) as session:
            api_url = f"{settings.backend_api_base_url}/run-backtesting"
            payload = {
                "start_time": start_time,
                "end_time": end_time,
                "backtesting_resolution": backtesting_resolution,
                "trade_cost": trade_cost,
                "config": config
            }
            
            async with session.post(api_url, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    # Extract backtesting results from the new API response format
                    backtesting_results = result.get("backtesting_results", {})
                    original_config = result.get("original_config", {})
                    success = result.get("success", False)
                    message = result.get("message", "")
                    
                    logger.info(f"run_backtesting completed: {backtesting_results}")
                    
                    # Return comprehensive backtesting information
                    return f"""Backtesting Completed Successfully!

{message}

Backtesting Results:
{json.dumps(backtesting_results, indent=2)}

Original Strategy Configuration:
{json.dumps(original_config, indent=2)}

Status: {'Success' if success else 'Failed'}"""
                else:
                    error_text = await response.text()
                    logger.error(f"run_backtesting failed: {error_text}")
                    return f"Backtesting failed: API returned status {response.status}: {error_text}"
        
    except Exception as e:
        logger.error(f"run_backtesting failed: {str(e)}", exc_info=True)
        raise ToolError(f"Failed to run backtesting: {str(e)}")


# Parameter Calculation Tools


@mcp.tool()
async def calculate_strategy_parameters(
    risk_level: Literal["conservative", "moderate", "aggressive"],
    trading_pair: str,
    volatility_level: Literal["low", "medium", "high"] = "medium",
    liquidity_level: Literal["low", "medium", "high"] = "medium",
    market_cap: Optional[float] = None,
    daily_volume: Optional[float] = None,
    spread_preference: Optional[float] = None,
    order_amount_preference: Optional[float] = None,
    refresh_time_preference: Optional[int] = None,
    leverage_preference: Optional[float] = None
) -> str:
    """Calculate optimal strategy parameters based on user preferences and market conditions.
    
    This tool uses the backend parameter calculator to determine optimal trading parameters
    including spread, order amounts, refresh times, and leverage based on user risk profile
    and asset characteristics.
    
    Args:
        risk_level: User's risk tolerance level ('conservative', 'moderate', 'aggressive')
        trading_pair: Trading pair symbol (e.g., 'BTC-USDT', 'ETH-USD')
        volatility_level: Asset volatility level ('low', 'medium', 'high'). Defaults to 'medium'.
        liquidity_level: Asset liquidity level ('low', 'medium', 'high'). Defaults to 'medium'.
        market_cap: Asset market capitalization in USD (optional)
        daily_volume: Asset daily trading volume in USD (optional)
        spread_preference: User's preferred spread percentage (optional, overrides calculated value)
        order_amount_preference: User's preferred order amount in USD (optional, overrides calculated value)
        refresh_time_preference: User's preferred refresh time in seconds (optional, overrides calculated value)
        leverage_preference: User's preferred leverage multiplier (optional, overrides calculated value)
    """
    try:
        logger.info(f"calculate_strategy_parameters: {risk_level} for {trading_pair}")
        
        # Base parameters for different risk levels
        risk_base_params = {
            "conservative": {
                'spread_base': 0.8,
                'order_amount_base': 500,
                'refresh_time_base': 120,
                'leverage_base': 1.0,
                'max_order_age_base': 1800,
                'price_ceiling_base': 2.0,
                'price_floor_base': 2.0
            },
            "moderate": {
                'spread_base': 0.5,
                'order_amount_base': 1000,
                'refresh_time_base': 90,
                'leverage_base': 2.0,
                'max_order_age_base': 1200,
                'price_ceiling_base': 3.0,
                'price_floor_base': 3.0
            },
            "aggressive": {
                'spread_base': 0.3,
                'order_amount_base': 2000,
                'refresh_time_base': 60,
                'leverage_base': 3.0,
                'max_order_age_base': 600,
                'price_ceiling_base': 5.0,
                'price_floor_base': 5.0
            }
        }
        
        # Volatility adjustments
        volatility_adjustments = {
            "low": {'spread_mult': 0.8, 'refresh_mult': 1.2},
            "medium": {'spread_mult': 1.0, 'refresh_mult': 1.0},
            "high": {'spread_mult': 1.5, 'refresh_mult': 0.7}
        }
        
        # Liquidity adjustments
        liquidity_adjustments = {
            "low": {'spread_mult': 1.5, 'order_mult': 0.5},
            "medium": {'spread_mult': 1.0, 'order_mult': 1.0},
            "high": {'spread_mult': 0.8, 'order_mult': 1.2}
        }
        
        # Get base parameters for risk level
        base_params = risk_base_params[risk_level]
        
        # Get adjustment factors
        vol_adj = volatility_adjustments[volatility_level]
        liq_adj = liquidity_adjustments[liquidity_level]
        
        # Calculate spread
        spread = base_params['spread_base'] * vol_adj['spread_mult'] * liq_adj['spread_mult']
        if spread_preference is not None:
            spread = spread_preference
        
        # Calculate order amount
        order_amount = base_params['order_amount_base'] * liq_adj['order_mult']
        if order_amount_preference is not None:
            order_amount = order_amount_preference
        
        # Calculate refresh time
        refresh_time = int(base_params['refresh_time_base'] * vol_adj['refresh_mult'])
        if refresh_time_preference is not None:
            refresh_time = refresh_time_preference
        
        # Calculate leverage
        leverage = base_params['leverage_base']
        if leverage_preference is not None:
            leverage = leverage_preference
        
        # Calculate other parameters
        max_order_age = base_params['max_order_age_base']
        price_ceiling = base_params['price_ceiling_base']
        price_floor = base_params['price_floor_base']
        
        # Apply market cap and volume adjustments if available
        if market_cap is not None and market_cap < 1000000000:  # < 1B
            spread *= 1.2  # Increase spread for smaller market cap
            order_amount *= 0.8  # Reduce order amount
        
        if daily_volume is not None and daily_volume < 10000000:  # < 10M
            spread *= 1.3  # Further increase spread for low volume
            order_amount *= 0.7  # Further reduce order amount
        
        # Format results
        result = {
            "trading_pair": trading_pair,
            "risk_level": risk_level,
            "calculated_parameters": {
                "spread_percentage": round(spread, 3),
                "order_amount_usd": round(order_amount, 2),
                "refresh_time_seconds": refresh_time,
                "leverage": round(leverage, 1),
                "max_order_age_seconds": max_order_age,
                "price_ceiling_percentage": round(price_ceiling, 1),
                "price_floor_percentage": round(price_floor, 1)
            },
            "asset_characteristics": {
                "volatility_level": volatility_level,
                "liquidity_level": liquidity_level,
                "market_cap": market_cap,
                "daily_volume": daily_volume
            },
            "user_preferences_applied": {
                "spread_preference": spread_preference,
                "order_amount_preference": order_amount_preference,
                "refresh_time_preference": refresh_time_preference,
                "leverage_preference": leverage_preference
            }
        }
        
        logger.info(f"calculate_strategy_parameters completed for {trading_pair}")
        return f"Strategy Parameters Calculated: {json.dumps(result, indent=2)}"
        
    except Exception as e:
        logger.error(f"calculate_strategy_parameters failed: {str(e)}", exc_info=True)
        raise ToolError(f"Failed to calculate strategy parameters: {str(e)}")


@mcp.tool()
async def validate_strategy_parameters(
    calculated_parameters: dict[str, Any],
    user_capital: float,
    user_risk_tolerance: Literal["conservative", "moderate", "aggressive"],
    strategy_type: str,
    controller_config: Optional[dict[str, Any]] = None
) -> str:
    """Validate strategy parameters against safety and consistency requirements.
    
    This tool performs comprehensive validation of calculated strategy parameters
    to ensure they meet safety requirements and align with user preferences.
    
    Args:
        calculated_parameters: Dictionary containing calculated strategy parameters
        user_capital: User's available trading capital in USD
        user_risk_tolerance: User's risk tolerance level
        strategy_type: Type of trading strategy being validated
        controller_config: Optional controller configuration to validate against
    """
    try:
        logger.info(f"validate_strategy_parameters: {strategy_type} with risk {user_risk_tolerance}")
        
        validation_results: Dict[str, Any] = {
            "validation_status": "passed",
            "warnings": [],
            "errors": [],
            "recommendations": []
        }
        
        warnings: List[str] = validation_results["warnings"]
        errors: List[str] = validation_results["errors"]
        recommendations: List[str] = validation_results["recommendations"]
        
        # Extract parameters for validation
        spread = calculated_parameters.get("spread_percentage", 0)
        order_amount = calculated_parameters.get("order_amount_usd", 0)
        leverage = calculated_parameters.get("leverage", 1)
        refresh_time = calculated_parameters.get("refresh_time_seconds", 60)
        
        # 1. Validate all parameters are calculated dynamically (no hardcoded values)
        if not calculated_parameters:
            errors.append("No calculated parameters provided")
        
        # 2. Validate risk parameters align with user's risk tolerance
        risk_limits = {
            "conservative": {"max_leverage": 2.0, "max_spread": 2.0, "min_refresh": 90},
            "moderate": {"max_leverage": 3.0, "max_spread": 1.5, "min_refresh": 60},
            "aggressive": {"max_leverage": 5.0, "max_spread": 1.0, "min_refresh": 30}
        }
        
        limits = risk_limits.get(user_risk_tolerance, risk_limits["conservative"])
        
        if leverage > limits["max_leverage"]:
            warnings.append(
                f"Leverage {leverage} exceeds recommended maximum {limits['max_leverage']} for {user_risk_tolerance} risk tolerance"
            )
        
        if spread > limits["max_spread"]:
            warnings.append(
                f"Spread {spread}% exceeds recommended maximum {limits['max_spread']}% for {user_risk_tolerance} risk tolerance"
            )
        
        if refresh_time < limits["min_refresh"]:
            warnings.append(
                f"Refresh time {refresh_time}s is below recommended minimum {limits['min_refresh']}s for {user_risk_tolerance} risk tolerance"
            )
        
        # 3. Validate order amounts within user's capital limits
        max_safe_order = user_capital * 0.1  # Max 10% of capital per order
        if order_amount > max_safe_order:
            errors.append(
                f"Order amount ${order_amount} exceeds safe limit of ${max_safe_order:.2f} (10% of capital)"
            )
        
        # 4. Validate position size respects user's capital and risk limits
        max_position_size = user_capital * 0.3  # Max 30% of capital in single position
        estimated_position = order_amount * leverage
        if estimated_position > max_position_size:
            warnings.append(
                f"Estimated position size ${estimated_position:.2f} exceeds recommended limit of ${max_position_size:.2f} (30% of capital)"
            )
        
        # 5. Validate leverage appropriate for user's risk tolerance and experience
        if user_risk_tolerance == "conservative" and leverage > 1.5:
            recommendations.append(
                "Consider reducing leverage for conservative risk profile"
            )
        
        # 6. Validate strategy-specific parameters
        required_fields = ["spread_percentage", "order_amount_usd", "refresh_time_seconds", "leverage"]
        missing_fields = [field for field in required_fields if field not in calculated_parameters]
        if missing_fields:
            errors.append(
                f"Missing required fields: {', '.join(missing_fields)}"
            )
        
        # 7. Validate controller_config maps correctly to strategy requirements
        if controller_config:
            if "controller_name" not in controller_config:
                warnings.append(
                    "Controller configuration missing controller_name"
                )
            
            if "controller_type" not in controller_config:
                warnings.append(
                    "Controller configuration missing controller_type"
                )
        
        # 8. Validate all required fields are present and properly typed
        type_validations = {
            "spread_percentage": (float, int),
            "order_amount_usd": (float, int),
            "refresh_time_seconds": (int,),
            "leverage": (float, int)
        }
        
        for field, expected_types in type_validations.items():
            if field in calculated_parameters:
                value = calculated_parameters[field]
                if not isinstance(value, expected_types):
                    type_names = [t.__name__ for t in expected_types] if isinstance(expected_types, tuple) else [expected_types.__name__]
                    errors.append(
                        f"Field '{field}' has incorrect type. Expected {' or '.join(type_names)}, got {type(value).__name__}"
                    )
        
        # 9. Validate position size and leverage combination maintains safe risk exposure
        risk_exposure = (order_amount * leverage) / user_capital
        max_risk_exposure = {
            "conservative": 0.05,  # 5%
            "moderate": 0.10,      # 10%
            "aggressive": 0.20     # 20%
        }
        
        max_exposure = max_risk_exposure.get(user_risk_tolerance, 0.05)
        if risk_exposure > max_exposure:
            errors.append(
                f"Risk exposure {risk_exposure:.1%} exceeds maximum {max_exposure:.1%} for {user_risk_tolerance} profile"
            )
        
        # Determine overall validation status
        if errors:
            validation_results["validation_status"] = "failed"
        elif warnings:
            validation_results["validation_status"] = "passed_with_warnings"
        
        # Add summary recommendations
        if validation_results["validation_status"] == "passed":
            recommendations.append(
                "All validation checks passed. Parameters are safe to use."
            )
        
        logger.info(f"validate_strategy_parameters completed: {validation_results['validation_status']}")
        return f"Strategy Parameters Validation: {json.dumps(validation_results, indent=2)}"
        
    except Exception as e:
        logger.error(f"validate_strategy_parameters failed: {str(e)}", exc_info=True)
        raise ToolError(f"Failed to validate strategy parameters: {str(e)}")


def create_ssl_context() -> Optional[ssl.SSLContext]:
    """Create SSL context if SSL is enabled"""
    if not settings.ssl_enabled:
        return None
        
    if not settings.ssl_cert_file or not settings.ssl_key_file:
        logger.warning("SSL enabled but cert/key files not specified. Running without SSL.")
        return None
        
    try:
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(settings.ssl_cert_file, settings.ssl_key_file)
        
        # Load CA file if specified
        if settings.ssl_ca_file:
            ssl_context.load_verify_locations(settings.ssl_ca_file)
            
        logger.info(f"SSL context created with cert: {settings.ssl_cert_file}")
        return ssl_context
    except Exception as e:
        logger.error(f"Failed to create SSL context: {e}")
        logger.warning("Running without SSL due to SSL configuration error.")
        return None


async def main(transport: Optional[str] = None, host: Optional[str] = None, port: Optional[int] = None):
    """Run the MCP server
    
    Args:
        transport: Transport type ("stdio" or "streamable-http")
        host: Host address for HTTP transport
        port: Port number for HTTP transport
    """
    # Use settings defaults if not provided
    transport = transport or settings.mcp_transport
    host = host or settings.mcp_host
    port = port or settings.mcp_port
    
    # Setup logging once at application start
    logger.info("Starting Hummingbot MCP Server")
    logger.info(f"API URL: {settings.api_url}")
    logger.info(f"Default Account: {settings.default_account}")
    logger.info(f"Transport: {transport}")
    if transport in ["streamable-http", "sse"]:
        ssl_context = create_ssl_context()
        protocol = "https" if ssl_context else "http"
        logger.info(f"Server: {protocol}://{host}:{port}")
        if ssl_context:
            logger.info("SSL enabled for secure connections")

    # Test API connection
    try:
        client = await hummingbot_client.initialize()
        accounts = await client.accounts.list_accounts()
        logger.info(f"Successfully connected to Hummingbot API. Found {len(accounts)} accounts.")
    except Exception as e:
        logger.error(f"Failed to connect to Hummingbot API: {e}")
        logger.error("Please ensure Hummingbot is running and API credentials are correct.")
        # Don't exit - let MCP server start anyway and handle errors per request

    # Run the server with FastMCP
    try:
        ssl_context = create_ssl_context() if transport in ["streamable-http", "sse"] else None
        
        if transport == "streamable-http":
            # Use streamable-http transport for HTTP access
            # Note: SSL context configuration may need to be handled at the application level
            if ssl_context:
                logger.warning("SSL context created but FastMCP may not support direct SSL configuration")
                logger.info("Consider using a reverse proxy (nginx/apache) for SSL termination in production")
            
            await mcp.run_async(
                transport="streamable-http",
                host=host,
                port=port,
                path="/mcp"
            )
        elif transport == "sse":
            # Use SSE transport for Server-Sent Events
            # Note: SSL context may not be supported for SSE transport
            if ssl_context:
                logger.warning("SSL context specified but may not be supported for SSE transport")
            await mcp.run_sse_async(
                host=host,
                port=port,
                path="/sse"
            )
        else:
            await mcp.run_stdio_async()
    finally:
        # Clean up client connection
        await hummingbot_client.close()


if __name__ == "__main__":
    asyncio.run(main())
