# utils/memory_manager.py
import json
import os
import asyncio
import aiofiles
from typing import Any, Dict
from core.logger import logger
from core.settings import settings

class MemoryManager:
    """
    Simple key-value JSON store for conversation context or other short-term memory.
    Uses async file operations with internal locking for thread safety.
    """
    def __init__(self, filepath: str = None):
        self.filepath = filepath if filepath else settings.get_memory_file_path()
        self._lock = asyncio.Lock()
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """Ensure the memory file exists with empty JSON object"""
        if not os.path.exists(self.filepath):
            try:
                os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
                with open(self.filepath, "w", encoding="utf-8") as f:
                    json.dump({}, f)
                logger.info(f"Initialized empty memory file: {self.filepath}")
            except IOError as e:
                logger.error(f"Could not initialize memory file {self.filepath}: {e}")

    async def load_context(self) -> Dict[str, Any]:
        """
        Load the entire context dict from the JSON file.
        Returns an empty dict if file not found or error.
        """
        async with self._lock:
            try:
                async with aiofiles.open(self.filepath, "r", encoding="utf-8") as f:
                    content = await f.read()
                    if content:
                        return json.loads(content)
                    return {}
            except FileNotFoundError:
                logger.warning(f"Memory file '{self.filepath}' not found. Returning empty context.")
                return {}
            except json.JSONDecodeError:
                logger.error(f"JSON decode error in memory file '{self.filepath}'. Returning empty context.")
                return {}
            except Exception as e:
                logger.error(f"Error loading context from '{self.filepath}': {e}", exc_info=True)
                return {}

    async def save_context(self, context: Dict[str, Any]) -> bool:
        """
        Persist the entire context dict to the JSON file.
        Returns True on success, False on failure.
        """
        async with self._lock:
            try:
                async with aiofiles.open(self.filepath, "w", encoding="utf-8") as f:
                    await f.write(json.dumps(context, indent=2))
                logger.debug(f"Context saved to '{self.filepath}'.")
                return True
            except Exception as e:
                logger.error(f"Error saving context to '{self.filepath}': {e}", exc_info=True)
                return False

    async def update_key(self, key: str, value: Any) -> bool:
        """Updates a specific key in the context."""
        context = await self.load_context()
        context[key] = value
        return await self.save_context(context)

    async def get_key(self, key: str, default: Any = None) -> Any:
        """Retrieves a specific key from the context."""
        context = await self.load_context()
        return context.get(key, default)

    async def clear_key(self, key: str) -> bool:
        """Removes a key from the context if it exists."""
        context = await self.load_context()
        if key in context:
            del context[key]
            return await self.save_context(context)
        return False

    async def clear_all_context(self) -> bool:
        """Clears all data from the context file."""
        return await self.save_context({})