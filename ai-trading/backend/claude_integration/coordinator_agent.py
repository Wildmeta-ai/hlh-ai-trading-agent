"""
Claude API Integration with MCP Tools
"""
import logging
from typing import Dict, Any, List, Optional

from .claude_client import ClaudeClient
from .tool_executor import ToolExecutor
from .message_processor import MessageProcessor

logger = logging.getLogger(__name__)


class ClaudeCoordinatorAgent:
    """Claude Coordinator Agent - Main Entry Coordinator"""

    def __init__(self):
        # Initialize all modules
        self.claude_client = ClaudeClient()
        self.tool_executor = ToolExecutor()
        self.message_processor = MessageProcessor(
            self.claude_client, self.tool_executor)
        logger.info(
            "Claude Coordinator Agent initialized with modular architecture")

    def _get_available_tools(self) -> List[Dict[str, Any]]:
        """Get available tools - delegate to tool executor"""
        return self.tool_executor.get_available_tools()

    async def execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool - delegate to tool executor"""
        return await self.tool_executor.execute_tool(tool_name, tool_input)

    async def process_message(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Process user message - delegate to message processor"""
        return await self.message_processor.process_message(user_message, conversation_history)


# Global instance
claude_agent = ClaudeCoordinatorAgent()


async def process_user_message(message: str, conversation_history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Process user message with Claude integration"""
    return await claude_agent.process_message(message, conversation_history)
