"""
Hyperliquid Connector for MCP Server
Provides trading functions and strategy deployment
"""
import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import requests
import hashlib
import hmac
from eth_account import Account
from eth_account.messages import encode_defunct

logger = logging.getLogger(__name__)

@dataclass
class HyperliquidCredentials:
    """Hyperliquid API credentials"""
    api_wallet: str
    api_key: str

class HyperliquidConnector:
    """
    Hyperliquid connector for trading operations
    Provides both read-only and trading functionality
    """
    
    def __init__(self, credentials: Optional[HyperliquidCredentials] = None):
        self.base_url = "https://api.hyperliquid.xyz"
        self.info_url = f"{self.base_url}/info"
        self.exchange_url = f"{self.base_url}/exchange"
        self.credentials = credentials
        
        # Default credentials from requirements
        if not credentials:
            self.credentials = HyperliquidCredentials(
                api_wallet="0x2eC15793D6171c1815B006e3D027f92F7E57B36F",
                api_key="0x3e1327394da35a1ff08485d4c4d810dc8d385833ed8b595a11b4f81837780e11"
            )
    
    async def get_market_info(self) -> Dict[str, Any]:
        """Get current market information"""
        try:
            request_data = {"type": "allMids"}
            response = requests.post(self.info_url, json=request_data)
            response.raise_for_status()
            
            all_mids = response.json()
            
            # Get meta information
            meta_request = {"type": "meta"}
            meta_response = requests.post(self.info_url, json=meta_request)
            meta_response.raise_for_status()
            meta_data = meta_response.json()
            
            return {
                "prices": all_mids,
                "meta": meta_data,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting market info: {e}")
            return {}
    
    async def get_user_state(self, user_address: Optional[str] = None) -> Dict[str, Any]:
        """Get user account state"""
        try:
            address = user_address or self.credentials.api_wallet
            request_data = {
                "type": "clearinghouseState",
                "user": address
            }
            
            response = requests.post(self.info_url, json=request_data)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            logger.error(f"Error getting user state: {e}")
            return {}
    
    async def get_user_positions(self, user_address: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get user's current positions"""
        try:
            user_state = await self.get_user_state(user_address)
            positions = []
            
            if "assetPositions" in user_state:
                for asset in user_state["assetPositions"]:
                    if asset.get("position", {}).get("szi", "0") != "0":
                        positions.append(asset["position"])
            
            return positions
        except Exception as e:
            logger.error(f"Error getting user positions: {e}")
            return []
    
    async def place_order(self, symbol: str, side: str, size: float, 
                         price: Optional[float] = None, order_type: str = "Limit") -> Dict[str, Any]:
        """
        Place an order on Hyperliquid
        
        Args:
            symbol: Trading symbol (e.g., "BTC")
            side: "Buy" or "Sell"
            size: Order size
            price: Order price (None for market orders)
            order_type: "Limit" or "Market"
        """
        try:
            # Build order payload
            order = {
                "coin": symbol,
                "is_buy": side.lower() == "buy",
                "sz": size,
                "limit_px": price if order_type == "Limit" else None,
                "order_type": {"limit": order_type == "Limit"},
                "reduce_only": False
            }
            
            # Create action payload
            action = {
                "type": "order",
                "orders": [order]
            }
            
            # Sign the request
            signed_payload = self._sign_request(action)
            
            response = requests.post(self.exchange_url, json=signed_payload)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return {"error": str(e)}
    
    async def cancel_order(self, coin: str, oid: int) -> Dict[str, Any]:
        """Cancel an existing order"""
        try:
            action = {
                "type": "cancel",
                "cancels": [{"coin": coin, "oid": oid}]
            }
            
            signed_payload = self._sign_request(action)
            
            response = requests.post(self.exchange_url, json=signed_payload)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Error canceling order: {e}")
            return {"error": str(e)}
    
    async def get_open_orders(self, user_address: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get user's open orders"""
        try:
            address = user_address or self.credentials.api_wallet
            request_data = {
                "type": "openOrders",
                "user": address
            }
            
            response = requests.post(self.info_url, json=request_data)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Error getting open orders: {e}")
            return []
    
    async def get_user_fills(self, user_address: Optional[str] = None, 
                           limit: int = 100) -> List[Dict[str, Any]]:
        """Get user's recent fills"""
        try:
            address = user_address or self.credentials.api_wallet
            request_data = {
                "type": "userFills",
                "user": address
            }
            
            response = requests.post(self.info_url, json=request_data)
            response.raise_for_status()
            
            fills = response.json()
            return fills[:limit] if fills else []
            
        except Exception as e:
            logger.error(f"Error getting user fills: {e}")
            return []
    
    def _sign_request(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Sign a request for authenticated endpoints"""
        try:
            # Create timestamp
            timestamp = int(datetime.now().timestamp() * 1000)
            
            # Create message to sign
            message_data = {
                "action": action,
                "nonce": timestamp,
                "vault": None
            }
            
            # Convert to JSON string
            message_str = json.dumps(message_data, separators=(',', ':'))
            
            # Create Ethereum signed message
            message = encode_defunct(text=message_str)
            
            # Sign with private key
            private_key = self.credentials.api_key
            signed_message = Account.sign_message(message, private_key)
            
            return {
                "action": action,
                "nonce": timestamp,
                "signature": {
                    "r": signed_message.r.to_bytes(32, 'big').hex(),
                    "s": signed_message.s.to_bytes(32, 'big').hex(),
                    "v": signed_message.v
                },
                "vault": None
            }
            
        except Exception as e:
            logger.error(f"Error signing request: {e}")
            raise

class HyperliquidMockConnector(HyperliquidConnector):
    """
    Mock connector for testing when Hyperliquid API is not available
    """
    
    def __init__(self):
        super().__init__()
        self.mock_positions = []
        self.mock_orders = []
        self.order_id_counter = 1000
    
    async def get_market_info(self) -> Dict[str, Any]:
        """Mock market info"""
        return {
            "prices": {
                "BTC": "45000.0",
                "ETH": "2500.0",
                "SOL": "100.0"
            },
            "meta": {
                "universe": [
                    {"name": "BTC", "maxLeverage": 50},
                    {"name": "ETH", "maxLeverage": 50},
                    {"name": "SOL", "maxLeverage": 20}
                ]
            },
            "timestamp": datetime.now().isoformat()
        }
    
    async def get_user_state(self, user_address: Optional[str] = None) -> Dict[str, Any]:
        """Mock user state"""
        return {
            "assetPositions": [
                {
                    "position": {
                        "coin": "BTC",
                        "szi": "0.1",
                        "entryPx": "44000.0",
                        "unrealizedPnl": "100.0",
                        "marginUsed": "880.0",
                        "leverage": {"type": "cross", "value": 5}
                    },
                    "type": "spot"
                }
            ],
            "crossMarginSummary": {
                "accountValue": "10000.0",
                "totalMarginUsed": "880.0",
                "totalNtlPos": "4500.0",
                "totalRawUsd": "9120.0"
            }
        }
    
    async def place_order(self, symbol: str, side: str, size: float, 
                         price: Optional[float] = None, order_type: str = "Limit") -> Dict[str, Any]:
        """Mock order placement"""
        order_id = self.order_id_counter
        self.order_id_counter += 1
        
        mock_order = {
            "oid": order_id,
            "coin": symbol,
            "side": side.lower(),
            "sz": size,
            "px": price or 0,
            "order_type": order_type,
            "timestamp": datetime.now().isoformat()
        }
        
        self.mock_orders.append(mock_order)
        
        return {
            "status": "ok",
            "response": {
                "type": "order",
                "data": {
                    "statuses": [{"resting": {"oid": order_id}}]
                }
            }
        }
    
    async def get_open_orders(self, user_address: Optional[str] = None) -> List[Dict[str, Any]]:
        """Mock open orders"""
        return self.mock_orders
    
    async def get_user_fills(self, user_address: Optional[str] = None, 
                           limit: int = 100) -> List[Dict[str, Any]]:
        """Mock user fills"""
        return [
            {
                "coin": "BTC",
                "side": "buy",
                "px": "44000.0",
                "sz": "0.1",
                "time": int(datetime.now().timestamp() * 1000),
                "fee": "4.4"
            }
        ]

# Test connectivity function
async def test_hyperliquid_connection() -> bool:
    """Test if Hyperliquid API is accessible"""
    try:
        connector = HyperliquidConnector()
        market_info = await connector.get_market_info()
        return bool(market_info.get("prices"))
    except Exception as e:
        logger.warning(f"Hyperliquid API not accessible: {e}")
        return False

# Factory function to get appropriate connector
async def get_hyperliquid_connector() -> HyperliquidConnector:
    """Get Hyperliquid connector (real or mock based on availability)"""
    if await test_hyperliquid_connection():
        logger.info("Using real Hyperliquid connector")
        return HyperliquidConnector()
    else:
        logger.info("Using mock Hyperliquid connector")
        return HyperliquidMockConnector()