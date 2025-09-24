import json
import logging
import os
import re
import sys
from typing import Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .claude_client import ClaudeClient as ClaudeClientType
    from .prompt_loader import PromptLoader as PromptLoaderType
else:
    # Runtime import with fallback
    try:
        from .claude_client import ClaudeClient
        from .prompt_loader import PromptLoader
    except ImportError:
        # Fallback for when running as script
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        try:
            from claude_integration.claude_client import ClaudeClient  # type: ignore
            from claude_integration.prompt_loader import PromptLoader  # type: ignore
        except ImportError:
            # Mock classes for when dependencies are not available
            class ClaudeClient:  # type: ignore
                def __init__(self):
                    pass

                async def create_message(self, **kwargs):
                    return {"content": [{"text": '{"strategies": []}'}]}

            class PromptLoader:  # type: ignore
                def __init__(self):
                    pass

                def load_prompt(self, name):
                    return "Mock prompt for testing"

logger = logging.getLogger(__name__)


class StrategyAgent:
    """AI Strategy Agent - LLM-based strategy generation"""

    def __init__(self):
        self.claude_client = ClaudeClient()
        logger.info("Strategy agent initialized")

    async def get_ai_strategy_recommendations(
        self,
        ai_profile: Dict[str, Any],
        trader_analysis: Dict[str, Any],
        user_preferences: Dict[str, Any],
        existing_strategy: Optional[Dict[str, Any]] = None,
        backtesting_results: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Get AI-driven strategy recommendations"""
        try:
            # Prepare analysis prompt
            analysis_prompt = self._create_strategy_analysis_prompt(
                ai_profile, trader_analysis, user_preferences, existing_strategy, backtesting_results)

            # Call Claude API to get strategy recommendations
            response = await self.claude_client.create_message(
                messages=[
                    {
                        "role": "user",
                        "content": analysis_prompt
                    }
                ],
                system=self._get_strategy_analysis_system_prompt(),
                model="claude-3-5-sonnet-20241022",
                max_tokens=2000,
                temperature=0.3,
                enable_mcp=False
            )

            # Parse Claude's response
            content = response.content[0].text if response.content else ""

            # Try to extract JSON from Claude's response
            try:
                # Look for JSON in response - improved regex for nested objects
                json_match = re.search(
                    r'\{(?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*\}', content, re.DOTALL)
                if json_match:
                    recommendations = json.loads(json_match.group())
                    logger.info(
                        f"Successfully parsed AI strategy recommendations with {len(recommendations.get('strategies', []))} strategies")
                    logger.info(f"Raw LLM response: {recommendations}")
                    return recommendations
                else:
                    # Fallback: create structured response from text
                    return self._parse_text_recommendations(content)
            except json.JSONDecodeError as e:
                logger.warning(
                    f"Failed to parse JSON from Claude response: {e}, using text parsing")
                return self._parse_text_recommendations(content)

        except Exception as e:
            logger.error(
                f"Error getting AI strategy recommendations: {e}", exc_info=True)
            return None

    def _get_strategy_analysis_system_prompt(self) -> str:
        """Get strategy analysis system prompt from external file"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        prompt_file = os.path.join(
            os.path.dirname(current_dir), "prompts", "strategy_agent_prompt.md")

        with open(prompt_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Convert markdown to plain text for Claude use
        # Remove markdown headers and formatting

        # Remove markdown headers
        content = re.sub(r'^#{1,6}\s+', '', content, flags=re.MULTILINE)

        # Remove code block markers
        content = re.sub(r'```json\n|```\n|```', '', content)

        # Remove bold/italic formatting
        content = re.sub(r'\*\*(.*?)\*\*', r'\1', content)
        content = re.sub(r'\*(.*?)\*', r'\1', content)

        # Remove bullet points
        content = re.sub(r'^\s*[-*]\s+', '', content, flags=re.MULTILINE)

        # Clean up extra whitespace
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)

        return content.strip()

    def _create_strategy_analysis_prompt(self, ai_profile: Dict[str, Any], trader_analysis: Dict[str, Any], user_preferences: Dict[str, Any], existing_strategy: Optional[Dict[str, Any]] = None, backtesting_results: Optional[Dict[str, Any]] = None) -> str:
        """Create analysis prompt - pass structured data to LLM"""
        prompt_data = {
            "ai_profile": ai_profile,
            "trader_analysis": trader_analysis,
            "user_preferences": user_preferences,
            "request": "generate_trading_strategies"
        }
        
        # Add optimization parameters if provided
        if existing_strategy:
            prompt_data["existing_strategy"] = existing_strategy
        if backtesting_results:
            prompt_data["backtesting_results"] = backtesting_results
            prompt_data["request"] = "optimize_trading_strategy"
            
        return json.dumps(prompt_data, indent=2)

    def _parse_text_recommendations(self, content: str) -> Dict[str, Any]:
        """Fallback for non-JSON responses - should be rare with proper prompting"""
        logger.error(
            "LLM failed to provide JSON response - this indicates prompt or model issues")

        # Return error structure - LLM should always provide structured JSON
        return {
            "strategies": [],
            "confidence": "low",
            "reasoning": "LLM failed to provide structured JSON response",
            "risk_assessment": "Cannot assess - invalid LLM response format",
            "market_conditions": "Cannot assess - invalid LLM response format",
            "error": "LLM response format error - expected JSON structure"
        }

    async def generate_strategies(self, ai_profile: Dict[str, Any], trader_analysis: Dict[str, Any], user_preferences: Dict[str, Any], existing_strategy: Optional[Dict[str, Any]] = None, backtesting_results: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate trading strategies based on AI recommendations - LLM must provide complete configurations

        IMPORTANT: This method enforces that LLM provides ALL strategy parameters dynamically.
        No hardcoded defaults are used for critical strategy fields to ensure:
        1. LLM generates parameters based on actual user data and preferences
        2. Each strategy is truly personalized and not template-based
        3. Strategy quality and relevance is maintained through intelligent parameter calculation
        """
        try:
            # Get AI recommendations
            ai_recommendations = await self.get_ai_strategy_recommendations(
                ai_profile, trader_analysis, user_preferences, existing_strategy, backtesting_results
            )

            if not ai_recommendations:
                logger.error("Failed to get AI recommendations")
                return {"strategies": [], "error": "Failed to generate AI recommendations"}

            # Check if LLM provided structured response
            if ai_recommendations.get("error"):
                logger.error(
                    f"LLM response error: {ai_recommendations.get('error')}")
                return {"strategies": [], "error": ai_recommendations.get('error')}

            # Process LLM-generated strategies - LLM should provide complete configurations
            strategies = []
            logger.info(f"Processing {len(ai_recommendations.get('strategies', []))} strategies from LLM")
            for i, strategy in enumerate(ai_recommendations.get("strategies", [])):
                logger.info(f"Strategy {i+1}: {strategy}")
                # Validate LLM provided all required fields - NO hardcoded defaults allowed
                required_fields = ["name", "type", "symbol", "controller_config"]
                missing_fields = [
                    field for field in required_fields if field not in strategy or strategy[field] is None]

                if missing_fields:
                    logger.error(
                        f"LLM failed to provide required fields: {missing_fields} for strategy: {strategy.get('name', 'Unknown')}")
                    logger.error(f"Strategy data: {strategy}")
                    logger.warning(
                        "Skipping incomplete strategy - hardcoded defaults removed to enforce LLM intelligence")
                    continue  # Skip this strategy if LLM didn't provide complete data

                # Build strategy following simplified StrategyConfig format - trust LLM output completely
                strategy_config = {
                    "name": strategy["name"],
                    "type": strategy["type"],
                    "symbol": strategy["symbol"],
                    "controller_config": strategy.get("controller_config", {})
                }

                strategies.append(strategy_config)

            return {
                "success": True,
                "strategies": strategies,
                "confidence": ai_recommendations.get("confidence", "medium")
            }

        except Exception as e:
            logger.error(f"Error generating strategies: {e}", exc_info=True)
            return {"success": False, "strategies": [], "error": str(e)}
