"""Claude Integration Package

This package contains all the modularized components for Claude AI integration:
- ClaudeClient: Core Claude API client
- ToolExecutor: MCP tool execution logic
- StrategyAnalyzer: AI strategy analysis functionality
- MessageProcessor: Message and conversation handling
- PromptLoader: Unified prompt file management
- ClaudeCoordinatorAgent: Main entry point (in coordinator_agent.py)
"""

from .coordinator_agent import ClaudeCoordinatorAgent
from .claude_client import ClaudeClient
from .tool_executor import ToolExecutor
from .strategy_agent import StrategyAgent
from .message_processor import MessageProcessor
from .prompt_loader import PromptLoader

__all__ = [
    'ClaudeCoordinatorAgent',
    'ClaudeClient',
    'ToolExecutor',
    'StrategyAnalyzer',
    'MessageProcessor',
    'PromptLoader'
]
