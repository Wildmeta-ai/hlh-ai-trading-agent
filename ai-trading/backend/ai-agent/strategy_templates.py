"""
Strategy templates for Hyperliquid perpetual trading
"""
from typing import Dict, Any, List
from dataclasses import dataclass
from enum import Enum

class StrategyType(Enum):
    CONSERVATIVE_MARKET_MAKER = "conservative_market_maker"
    AGGRESSIVE_SCALPER = "aggressive_scalper"
    RSI_DIRECTIONAL = "rsi_directional"
    MACD_TREND = "macd_trend"

@dataclass
class StrategyConfig:
    """Base strategy configuration"""
    name: str
    type: StrategyType
    symbol: str
    leverage: float
    position_size: float
    risk_per_trade: float
    parameters: Dict[str, Any]
    
    def to_hummingbot_config(self) -> Dict[str, Any]:
        """Convert to Hummingbot configuration format"""
        base_config = {
            "strategy": self.type.value,
            "market": f"{self.symbol}_USDT",
            "leverage": self.leverage,
            "position_size_usd": self.position_size,
            "risk_per_trade": self.risk_per_trade,
        }
        base_config.update(self.parameters)
        return base_config

class StrategyTemplates:
    """Strategy template definitions"""
    
    @staticmethod
    def conservative_market_maker(symbol: str = "BTC", base_position_size: float = 1000) -> StrategyConfig:
        """Conservative Market Maker: Low leverage, wide spreads"""
        return StrategyConfig(
            name="Conservative Market Maker",
            type=StrategyType.CONSERVATIVE_MARKET_MAKER,
            symbol=symbol,
            leverage=2.0,
            position_size=base_position_size,
            risk_per_trade=0.01,  # 1% risk per trade
            parameters={
                "bid_spread": 0.002,  # 0.2% below mid
                "ask_spread": 0.002,  # 0.2% above mid
                "order_refresh_time": 30,  # 30 seconds
                "inventory_skew_enabled": True,
                "max_inventory_ratio": 0.3,
                "stop_loss_pct": 0.05,  # 5% stop loss
                "take_profit_pct": 0.03,  # 3% take profit
                "min_profitability": 0.001  # 0.1% minimum profit
            }
        )
    
    @staticmethod
    def aggressive_scalper(symbol: str = "BTC", base_position_size: float = 2000) -> StrategyConfig:
        """Aggressive Scalper: High frequency, tight spreads"""
        return StrategyConfig(
            name="Aggressive Scalper",
            type=StrategyType.AGGRESSIVE_SCALPER,
            symbol=symbol,
            leverage=5.0,
            position_size=base_position_size,
            risk_per_trade=0.005,  # 0.5% risk per trade
            parameters={
                "bid_spread": 0.0005,  # 0.05% below mid
                "ask_spread": 0.0005,  # 0.05% above mid
                "order_refresh_time": 5,  # 5 seconds
                "inventory_skew_enabled": True,
                "max_inventory_ratio": 0.1,
                "stop_loss_pct": 0.02,  # 2% stop loss
                "take_profit_pct": 0.01,  # 1% take profit
                "min_profitability": 0.0002,  # 0.02% minimum profit
                "max_orders_per_side": 3
            }
        )
    
    @staticmethod
    def rsi_directional(symbol: str = "BTC", base_position_size: float = 1500) -> StrategyConfig:
        """RSI Directional: Technical trend following"""
        return StrategyConfig(
            name="RSI Directional",
            type=StrategyType.RSI_DIRECTIONAL,
            symbol=symbol,
            leverage=3.0,
            position_size=base_position_size,
            risk_per_trade=0.02,  # 2% risk per trade
            parameters={
                "rsi_period": 14,
                "rsi_overbought": 70,
                "rsi_oversold": 30,
                "rsi_timeframe": "5m",
                "entry_threshold": 5,  # RSI points from overbought/oversold
                "exit_threshold": 50,  # RSI neutral zone
                "stop_loss_pct": 0.03,  # 3% stop loss
                "take_profit_pct": 0.04,  # 4% take profit
                "trailing_stop_pct": 0.015,  # 1.5% trailing stop
                "min_volume_24h": 1000000  # Minimum 24h volume
            }
        )
    
    @staticmethod
    def macd_trend(symbol: str = "BTC", base_position_size: float = 1800) -> StrategyConfig:
        """MACD Trend: Multi-timeframe positioning"""
        return StrategyConfig(
            name="MACD Trend",
            type=StrategyType.MACD_TREND,
            symbol=symbol,
            leverage=4.0,
            position_size=base_position_size,
            risk_per_trade=0.015,  # 1.5% risk per trade
            parameters={
                "fast_period": 12,
                "slow_period": 26,
                "signal_period": 9,
                "macd_timeframe": "15m",
                "trend_timeframe": "1h",
                "entry_confirmation": "signal_crossover",
                "exit_condition": "signal_reverse",
                "stop_loss_pct": 0.025,  # 2.5% stop loss
                "take_profit_pct": 0.05,  # 5% take profit
                "position_scaling": True,  # Scale position based on signal strength
                "max_position_multiplier": 1.5
            }
        )
    
    @staticmethod
    def get_all_templates() -> List[StrategyConfig]:
        """Get all available strategy templates"""
        return [
            StrategyTemplates.conservative_market_maker(),
            StrategyTemplates.aggressive_scalper(),
            StrategyTemplates.rsi_directional(),
            StrategyTemplates.macd_trend()
        ]
    
    @staticmethod
    def get_template_by_type(strategy_type: StrategyType, **kwargs) -> StrategyConfig:
        """Get strategy template by type with optional parameters"""
        template_map = {
            StrategyType.CONSERVATIVE_MARKET_MAKER: StrategyTemplates.conservative_market_maker,
            StrategyType.AGGRESSIVE_SCALPER: StrategyTemplates.aggressive_scalper,
            StrategyType.RSI_DIRECTIONAL: StrategyTemplates.rsi_directional,
            StrategyType.MACD_TREND: StrategyTemplates.macd_trend
        }
        
        if strategy_type not in template_map:
            raise ValueError(f"Unknown strategy type: {strategy_type}")
        
        return template_map[strategy_type](**kwargs)

class StrategySelector:
    """AI-based strategy selection based on trader profile"""
    
    @staticmethod
    def select_strategies(trader_profile: Dict[str, Any], 
                         technical_metrics: Dict[str, Any]) -> List[StrategyConfig]:
        """
        Select appropriate strategies based on trader profile and technical metrics
        """
        selected_strategies = []
        
        # Extract key metrics
        risk_level = trader_profile.get("labels", [])
        trading_style = trader_profile.get("trader", "")
        market_adaptability = technical_metrics.get("market_adaptability", {})
        
        # High leverage traders -> Aggressive Scalper
        if any("leverage" in label.lower() for label in risk_level):
            selected_strategies.append(
                StrategyTemplates.aggressive_scalper(base_position_size=2500)
            )
        
        # Trend followers -> MACD Trend
        trend_following = market_adaptability.get("trend_following", 0.5)
        if trend_following > 0.6:
            selected_strategies.append(
                StrategyTemplates.macd_trend(base_position_size=2000)
            )
        
        # High volatility traders -> RSI Directional
        high_volatility = market_adaptability.get("high_volatility", 0.5)
        if high_volatility > 0.6:
            selected_strategies.append(
                StrategyTemplates.rsi_directional(base_position_size=1800)
            )
        
        # Conservative fallback -> Market Maker
        if not selected_strategies or "conservative" in trading_style.lower():
            selected_strategies.append(
                StrategyTemplates.conservative_market_maker(base_position_size=1500)
            )
        
        return selected_strategies[:2]  # Return max 2 strategies