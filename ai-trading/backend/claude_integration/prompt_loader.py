import os
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class PromptLoader:
    """Prompt Loader - Unified management of prompt file loading"""

    def __init__(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        # prompts directory is in the backend folder, not in claude_integration
        backend_dir = os.path.dirname(self.current_dir)
        self.prompts_dir = os.path.join(backend_dir, "prompts")
        logger.info("Prompt loader initialized")

    def get_coordinator_agent_prompt(self) -> str:
        """Get coordinator agent prompt"""
        try:
            prompt_file = os.path.join(self.prompts_dir, "coordinator_agent_prompt.md")

            with open(prompt_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Convert markdown to plain text for Claude use
            content = self._clean_markdown(content)

            return content.strip()

        except FileNotFoundError:
            logger.error("System prompt file not found")
            raise
        except Exception as e:
            logger.error(f"Error reading system prompt: {e}")
            raise

    def get_strategy_analysis_prompt(self) -> str:
        """Get strategy analysis prompt"""
        try:
            prompt_file = os.path.join(
                self.prompts_dir, "strategy_analysis_prompt.md")

            with open(prompt_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Convert markdown to plain text for Claude use
            content = self._clean_markdown(content)

            return content.strip()

        except FileNotFoundError:
            logger.error("Strategy analysis prompt file not found")
            raise
        except Exception as e:
            logger.error(f"Error reading strategy analysis prompt: {e}")
            raise

    def _clean_markdown(self, content: str) -> str:
        """Clean Markdown formatting, convert to plain text"""
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

        return content

    def load_custom_prompt(self, filename: str) -> Optional[str]:
        """Load custom prompt file"""
        try:
            prompt_file = os.path.join(self.prompts_dir, filename)

            with open(prompt_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # If it's a markdown file, clean formatting
            if filename.endswith('.md'):
                content = self._clean_markdown(content)

            return content.strip()

        except FileNotFoundError:
            logger.warning(f"Custom prompt file {filename} not found")
            return None
        except Exception as e:
            logger.error(f"Error reading custom prompt {filename}: {e}")
            return None

    def list_available_prompts(self) -> list:
        """List available prompt files"""
        try:
            if not os.path.exists(self.prompts_dir):
                return []

            files = []
            for filename in os.listdir(self.prompts_dir):
                if filename.endswith(('.md', '.txt')):
                    files.append(filename)

            return sorted(files)

        except Exception as e:
            logger.error(f"Error listing prompt files: {e}")
            return []
