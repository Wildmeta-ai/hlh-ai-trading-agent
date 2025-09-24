"""
AI Agent Processing Module
Analyzes trader data and generates trading strategies
"""
import json
from typing import Dict, Any, List, Optional
from dataclasses import asdict
import logging

import sys
import importlib.util
import os

# Add the current directory to the path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Import strategy_templates
spec = importlib.util.spec_from_file_location("strategy_templates", os.path.join(current_dir, "strategy_templates.py"))
strategy_templates = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strategy_templates)

StrategySelector = strategy_templates.StrategySelector
StrategyConfig = strategy_templates.StrategyConfig
StrategyType = strategy_templates.StrategyType

logger = logging.getLogger(__name__)

class AITradingAgent:
    """Main AI agent for processing trader data and generating strategies"""
    
    def __init__(self):
        self.strategy_selector = StrategySelector()
    
    def analyze_trader_behavior(self, trader_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze trader behavior and extract key insights
        """
        ai_profile = trader_analysis.get("ai_profile", {})
        technical_metrics = trader_analysis.get("technical_metrics", {})
        trade_story = trader_analysis.get("trade_story", [])
        
        # Extract behavioral patterns
        behavior_analysis = {
            "risk_profile": self._analyze_risk_profile(ai_profile, technical_metrics),
            "trading_style": self._analyze_trading_style(ai_profile, trade_story),
            "market_adaptability": self._analyze_market_adaptability(technical_metrics),
            "strengths": ai_profile.get("labels", []),
            "weaknesses": ai_profile.get("insights", []),
            "suggestions": ai_profile.get("suggestion", "")
        }
        
        return behavior_analysis
    
    def _analyze_risk_profile(self, ai_profile: Dict, technical_metrics: Dict) -> Dict[str, Any]:
        """Analyze risk profile from trader data"""
        profile_data = technical_metrics.get("profile", {})
        statistics = technical_metrics.get("statistics", {})
        
        return {
            "risk_level": profile_data.get("risk_level", "medium"),
            "leverage_usage": self._extract_leverage_info(ai_profile),
            "max_drawdown": statistics.get("max_drawdown", 0),
            "win_rate": self._calculate_win_rate(statistics),
            "risk_tolerance": self._assess_risk_tolerance(ai_profile)
        }
    
    def _analyze_trading_style(self, ai_profile: Dict, trade_story: List) -> Dict[str, Any]:
        """Analyze trading style patterns"""
        return {
            "style_description": ai_profile.get("trader", ""),
            "nickname": ai_profile.get("nickname", ""),
            "dominant_patterns": self._extract_patterns(trade_story),
            "preferred_instruments": self._extract_preferred_instruments(trade_story),
            "holding_periods": self._analyze_holding_periods(trade_story)
        }
    
    def _analyze_market_adaptability(self, technical_metrics: Dict) -> Dict[str, Any]:
        """Analyze market adaptability metrics"""
        adaptability = technical_metrics.get("market_adaptability", {})
        
        return {
            "trend_following": adaptability.get("trend_following", 0.5),
            "bull_market": adaptability.get("bull_market", 0.5),
            "bear_market": adaptability.get("bear_market", 0.5),
            "sideways_market": adaptability.get("sideways_market", 0.5),
            "high_volatility": adaptability.get("high_volatility", 0.5),
            "low_volatility": adaptability.get("low_volatility", 0.5)
        }
    
    def generate_strategies(self, trader_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate customized trading strategies based on trader analysis
        """
        behavior_analysis = self.analyze_trader_behavior(trader_analysis)
        
        # Select appropriate strategies
        ai_profile = trader_analysis.get("ai_profile", {})
        technical_metrics = trader_analysis.get("technical_metrics", {})
        
        selected_strategies = self.strategy_selector.select_strategies(
            ai_profile, technical_metrics
        )
        
        # Customize strategies based on behavior analysis
        customized_strategies = []
        for strategy in selected_strategies:
            customized_strategy = self._customize_strategy(strategy, behavior_analysis)
            customized_strategies.append(customized_strategy)
        
        return {
            "strategies": [asdict(s) for s in customized_strategies],
            "behavior_analysis": behavior_analysis,
            "recommendations": self._generate_recommendations(behavior_analysis),
            "risk_warnings": self._generate_risk_warnings(behavior_analysis)
        }
    
    def _customize_strategy(self, strategy: StrategyConfig, 
                           behavior_analysis: Dict[str, Any]) -> StrategyConfig:
        """Customize strategy based on trader behavior analysis"""
        risk_profile = behavior_analysis.get("risk_profile", {})
        
        # Adjust leverage based on risk tolerance
        risk_level = risk_profile.get("risk_level", "medium")
        if risk_level == "high":
            strategy.leverage = min(strategy.leverage * 1.5, 10.0)
        elif risk_level == "low":
            strategy.leverage = max(strategy.leverage * 0.7, 1.0)
        
        # Adjust position sizes based on max drawdown history
        max_drawdown = risk_profile.get("max_drawdown", 0)
        if max_drawdown > 0.3:  # If historical max drawdown > 30%
            strategy.position_size *= 0.7  # Reduce position size
            strategy.risk_per_trade *= 0.8  # Reduce risk per trade
        
        # Adjust parameters based on win rate
        win_rate = risk_profile.get("win_rate", 0.5)
        if win_rate < 0.4:  # Low win rate
            # Tighten stop losses and widen take profits
            if "stop_loss_pct" in strategy.parameters:
                strategy.parameters["stop_loss_pct"] *= 0.8
            if "take_profit_pct" in strategy.parameters:
                strategy.parameters["take_profit_pct"] *= 1.3
        
        return strategy
    
    def _generate_recommendations(self, behavior_analysis: Dict[str, Any]) -> List[str]:
        """Generate trading recommendations based on behavior analysis"""
        recommendations = []
        
        risk_profile = behavior_analysis.get("risk_profile", {})
        
        if risk_profile.get("leverage_usage", "medium") == "high":
            recommendations.append("Consider reducing leverage usage to manage risk better")
        
        if risk_profile.get("win_rate", 0.5) < 0.4:
            recommendations.append("Focus on improving entry timing and risk management")
        
        if risk_profile.get("max_drawdown", 0) > 0.3:
            recommendations.append("Implement stricter position sizing and stop-loss rules")
        
        return recommendations
    
    def _generate_risk_warnings(self, behavior_analysis: Dict[str, Any]) -> List[str]:
        """Generate risk warnings based on behavior analysis"""
        warnings = []
        
        risk_profile = behavior_analysis.get("risk_profile", {})
        
        if risk_profile.get("risk_tolerance", "medium") == "very_high":
            warnings.append("⚠️ High risk tolerance detected - monitor position sizes carefully")
        
        if risk_profile.get("max_drawdown", 0) > 0.5:
            warnings.append("🚨 Historical large drawdowns - consider capital preservation strategies")
        
        return warnings
    
    # Helper methods
    def _extract_leverage_info(self, ai_profile: Dict) -> str:
        """Extract leverage usage from AI profile"""
        labels = ai_profile.get("labels", [])
        if any("leverage" in label.lower() for label in labels):
            return "high"
        elif any("conservative" in label.lower() for label in labels):
            return "low"
        return "medium"
    
    def _calculate_win_rate(self, statistics: Dict) -> float:
        """Calculate win rate from statistics"""
        total_trades = statistics.get("total_trades", 0)
        winning_trades = statistics.get("winning_trades", 0)
        
        if total_trades == 0:
            return 0.5  # Default neutral
        
        return winning_trades / total_trades
    
    def _assess_risk_tolerance(self, ai_profile: Dict) -> str:
        """Assess risk tolerance from AI profile"""
        trader_desc = ai_profile.get("trader", "").lower()
        labels = [label.lower() for label in ai_profile.get("labels", [])]
        
        high_risk_keywords = ["leverage", "risk", "aggressive", "daredevil"]
        low_risk_keywords = ["conservative", "cautious", "safe"]
        
        if any(keyword in trader_desc for keyword in high_risk_keywords) or \
           any(any(keyword in label for keyword in high_risk_keywords) for label in labels):
            return "very_high"
        elif any(keyword in trader_desc for keyword in low_risk_keywords) or \
             any(any(keyword in label for keyword in low_risk_keywords) for label in labels):
            return "low"
        
        return "medium"
    
    def _extract_patterns(self, trade_story: List) -> List[str]:
        """Extract trading patterns from trade stories"""
        if not trade_story:
            return []
        
        patterns = []
        for story in trade_story:
            if isinstance(story, dict):
                story_type = story.get("story_type", "")
                symbol = story.get("symbol", "")
                if story_type and symbol:
                    patterns.append(f"{symbol}: {story_type}")
        
        return patterns[:5]  # Return top 5 patterns
    
    def _extract_preferred_instruments(self, trade_story: List) -> List[str]:
        """Extract preferred trading instruments"""
        if not trade_story:
            return []
        
        instruments = {}
        for story in trade_story:
            if isinstance(story, dict):
                symbol = story.get("symbol", "")
                if symbol:
                    instruments[symbol] = instruments.get(symbol, 0) + 1
        
        # Sort by frequency
        sorted_instruments = sorted(instruments.items(), key=lambda x: x[1], reverse=True)
        return [instrument[0] for instrument in sorted_instruments[:3]]
    
    def _analyze_holding_periods(self, trade_story: List) -> Dict[str, Any]:
        """Analyze holding period preferences"""
        if not trade_story:
            return {"average_hours": 0, "style": "unknown"}
        
        total_hours = 0
        count = 0
        
        for story in trade_story:
            if isinstance(story, dict):
                opened_at = story.get("opened_at")
                closed_at = story.get("closed_at")
                if opened_at and closed_at:
                    # This would need proper datetime parsing in real implementation
                    count += 1
        
        if count == 0:
            return {"average_hours": 0, "style": "unknown"}
        
        avg_hours = total_hours / count if count > 0 else 0
        
        if avg_hours < 1:
            style = "scalping"
        elif avg_hours < 24:
            style = "day_trading"
        elif avg_hours < 168:  # 1 week
            style = "swing_trading"
        else:
            style = "position_trading"
        
        return {"average_hours": avg_hours, "style": style}

# Convenience function
def process_trader_data(trader_analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main function to process trader data and generate strategies
    
    Args:
        trader_analysis: Complete trader analysis data from APIs
        
    Returns:
        Dict containing strategies, behavior analysis, and recommendations
    """
    agent = AITradingAgent()
    return agent.generate_strategies(trader_analysis)