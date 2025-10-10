# core/plugin_interface.py
"""
Defines the Plugin interface that all plugins must implement.
"""
from typing import Dict, Any, List, Optional

class Plugin:
    def __init__(self, name: str, description: str, shared_resources: Optional[Dict[str, Any]] = None):
        self.name = name
        self.description = description
        self.shared_resources = shared_resources if shared_resources else {}
        # Example: self.db = shared_resources.get('db')

    async def run(self, *args, **kwargs) -> None:
        """
        Called when the plugin is loaded.
        Can be used for initialization tasks or starting background processes.
        """
        pass # Default implementation does nothing.

    async def execute_command(self, command_text: str, intent_data: Dict[str, Any], **kwargs) -> str:
        """
        Execute a command intended for this plugin based on parsed intent.

        :param command_text: The raw command text from the user.
        :param intent_data: Dictionary from NLPProcessor, typically contains:
                            `{'intent': str, 'entities': Dict[str, Any], 'original_command': str}`.
                            Entities can vary based on the intent.
        :param kwargs: Additional keyword arguments that might be passed.
        :return: A string response for the user.
        :raises NotImplementedError: If the plugin does not implement this method.
        """ # Suggestion 1.3.2: Document intent_data format
        raise NotImplementedError(f"Plugin '{self.name}' must implement command execution.")

    def get_supported_intents(self) -> List[str]:
        """
        Optional: Returns a list of intent strings this plugin can handle.
        Used by DialogueManager for routing commands.
        """
        return []

    @staticmethod
    def get_required_resources() -> List[str]:
        """
        Optional: Static method plugins can override to declare shared resource keys
        they need injected into their constructor from the main application.
        Example: `return ['db', 'audio_manager', 'task_manager']`
        """
        return []

    def supports_intent(self, intent_name: str) -> bool: # Suggestion 1.3.3
        """
        Checks if this plugin supports the given intent name.
        Helper method based on get_supported_intents().
        """
        return intent_name in self.get_supported_intents()
