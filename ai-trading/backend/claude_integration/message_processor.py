import json
import logging
import re
from typing import Dict, Any, List, Optional, Tuple

from .claude_client import ClaudeClient
from .tool_executor import ToolExecutor
from .prompt_loader import PromptLoader

logger = logging.getLogger(__name__)


class MessageProcessor:
    """Message Processor - Handle conversation logic and response formatting"""

    def __init__(self, claude_client: ClaudeClient, tool_executor: ToolExecutor):
        self.claude_client = claude_client
        self.tool_executor = tool_executor
        self.prompt_loader = PromptLoader()
        logger.info("Message processor initialized")

    async def process_message(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Process user message and return Claude response"""
        try:
            # Let AI naturally handle wallet address detection and analysis
            # No preprocessing needed - Claude will intelligently identify wallet addresses in context

            # Prepare messages for Claude (using conversation history provided by client)
            messages = []

            # Add conversation history from client (last 10 messages to avoid token limits)
            if conversation_history:
                recent_history = conversation_history[-10:] if len(
                    conversation_history) > 10 else conversation_history
                for msg in recent_history:
                    if msg.get("role") in ["user", "assistant"]:
                        messages.append({
                            "role": msg["role"],
                            "content": msg["content"]
                        })

            # Add current user message
            messages.append({
                "role": "user",
                "content": user_message
            })

            # Process message with Claude and tools enabled
            logger.info("Processing message with Claude and tools")

            # Call Claude with tools enabled for coordinator agent functionality
            response = await self.claude_client.create_message(
                messages=messages,
                system=self.prompt_loader.get_coordinator_agent_prompt(),
                tools=self.tool_executor.get_available_tools()
            )
            
            logger.info("Claude response received successfully")

            # Extract text content from Claude response
            response_content = ""
            for content_block in response.content:
                if content_block.type == "text":
                    response_content += content_block.text
            
            # Try to parse as JSON first (coordinator agent should return JSON)
            # First, try to parse as pure JSON
            try:
                parsed_response = json.loads(response_content)
                if isinstance(parsed_response, dict):
                    return parsed_response
                else:
                    # If parsed but not a dict, wrap it
                    return {"content": str(parsed_response)}
            except json.JSONDecodeError:
                pass
            
            # If not pure JSON, try to extract JSON from within the text
            import re
            json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
            json_matches = re.findall(json_pattern, response_content)
            
            for match in json_matches:
                try:
                    parsed_json = json.loads(match)
                    if isinstance(parsed_json, dict):
                        return parsed_json
                except json.JSONDecodeError:
                    continue
            
            # If no valid JSON found, wrap the content
            return {"content": response_content}

        except Exception as e:
            logger.error(f"Claude processing error: {e}")
            error_response = {
                "content": f"Error: {str(e)}",
                "error": str(e)
            }
            return error_response
