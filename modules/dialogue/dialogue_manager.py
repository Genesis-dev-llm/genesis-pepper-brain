# modules/dialogue/dialogue_manager.py
import asyncio
import os
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Dict, Any, Optional, Callable, Coroutine, Union

from core.logger import logger
from core.settings import settings
from modules.external_ai import ExternalAI
from modules.dialogue.gemini_adapter import stylize_with_gemini
from modules.utils.personality_loader import load_personalities
from modules.nlp_processor import ( 
    INTENT_SET_REMINDER, INTENT_TELL_TIME, INTENT_TELL_DATE, 
    INTENT_CHANGE_PERSONALITY, INTENT_CHANGE_TONE,
    INTENT_UNKNOWN, INTENT_GENERAL_QUERY
)
from modules.response_formatter import format_error_message 

if TYPE_CHECKING:
    from modules.nlp_processor import NLPProcessor
    from utils.memory_manager import MemoryManager
    from types import SimpleNamespace
    from core.plugin_interface import Plugin
    from modules.personalities.profile import PersonaProfile
    from modules.pepper_interface import PepperInterface
    from modules.decision_engine import DecisionEngine

class DialogueManager:
    def __init__(
        self, 
        nlp_processor: 'NLPProcessor', 
        memory_manager: 'MemoryManager', 
        modules_facade: 'SimpleNamespace',
        plugins_dict: Dict[str, 'Plugin'],
        pepper_interface: 'PepperInterface'
    ):
        self.nlp_processor = nlp_processor
        self.memory = memory_manager
        self.modules_facade = modules_facade
        self.plugins = plugins_dict
        self.pepper_interface = pepper_interface 

        self.personality_enabled = settings.use_gemini_styling
        
        self.personalities: Dict[str, 'PersonaProfile'] = {}
        self.current_persona: Optional['PersonaProfile'] = None
        self.current_tone: Optional[str] = None
        
        self._load_and_set_initial_persona()

        # Initialize DecisionEngine after DM is set up to break circular dependency
        from modules.decision_engine import DecisionEngine 
        self.decision_engine = DecisionEngine(
            pepper_interface=self.pepper_interface,
            nlp_processor=self.nlp_processor,
            modules_facade=self.modules_facade,
            dialogue_manager=self
        )

        # Intent dispatch table (ONLY for internal, simple actions or state changes)
        self.intent_handlers: Dict[str, Callable[[Dict[str, Any], str], Coroutine[Any, Any, str]]] = {
            INTENT_TELL_TIME: self._handle_tell_time,
            INTENT_TELL_DATE: self._handle_tell_date,
            INTENT_SET_REMINDER: self._handle_set_reminder,
            INTENT_CHANGE_PERSONALITY: self._handle_change_personality, 
            INTENT_CHANGE_TONE: self._handle_change_tone,
        }
        logger.info(f"DialogueManager initialized. Initial Persona: {self.current_persona.name if self.current_persona else 'None'}. DecisionEngine ready.")

    def _load_and_set_initial_persona(self):
        """Load personality profiles and set initial persona"""
        loaded_persona_ns = load_personalities()
        self.personalities = {
            name.lower(): getattr(loaded_persona_ns, name) 
            for name in dir(loaded_persona_ns) 
            if not name.startswith('_') and hasattr(getattr(loaded_persona_ns, name), '__class__')
        }

        initial_persona_name = settings.personality.lower()
        self.current_persona = self.personalities.get(initial_persona_name)
        
        if not self.current_persona and self.personalities:
            self.current_persona = list(self.personalities.values())[0]
        
        if self.current_persona:
            self.current_tone = self.current_persona.tone
            logger.info(f"Initial persona set: {self.current_persona.name}")
        else:
            logger.warning("No personas loaded. Using default configuration.")

    def log_interaction(self, user_input: str, genesis_response: str):
        """Log user interaction to file"""
        try:
            ts = datetime.now(timezone.utc).isoformat()
            log_path = settings.get_interactions_log_path()
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"{ts} | User: {user_input}\n")
                f.write(f"{ts} | GENESIS: {genesis_response}\n\n")
        except Exception as e:
            logger.error(f"Error logging interaction to file '{log_path}': {e}", exc_info=False)

    async def handle_sensor_callback(self, sensor_data: Dict[str, Any]) -> None:
        """
        Entry point for all sensor inputs coming from the PepperInterface.
        Decides how to process the event (speech, touch, vision).
        """
        event_name = sensor_data.get("event_name")
        event_value = sensor_data.get("value")
        
        logger.info(f"DM received sensor event: {event_name}", extra={"value_snippet": str(event_value)[:50]})
        
        if event_name == "WordRecognized":
            # Extract recognized text from event value
            if isinstance(event_value, list) and len(event_value) > 0:
                user_text = str(event_value[0])
            else:
                user_text = str(event_value)
            
            if user_text and user_text.strip():
                # Delegate speech processing to the Decision Engine
                asyncio.create_task(self.decision_engine.process_user_speech(user_text))
        
        elif event_name == "ALMemory/Touched":
            # Example: Robot head touched
            if isinstance(event_value, list) and len(event_value) >= 2:
                if event_value[1] == 1:  # Touch detected
                    await self.pepper_interface.speak_async("Please don't touch my head.")
        
        # Add more sensor handlers here (Vision, Sonar, etc.)

    async def process_turn(self, raw_text: str) -> str:
        """
        Legacy text processing entry point (used internally for simple commands).
        Returns the response string *without* speaking it.
        """
        parsed_command = self.nlp_processor.parse_command(raw_text)
        intent = parsed_command.get("intent", INTENT_UNKNOWN)
        entities = parsed_command.get("entities", {})

        # 1. Handle hardcoded simple intents
        if intent in self.intent_handlers:
            handler = self.intent_handlers[intent]
            base_reply = await self._handle_intent_with_error_handling(handler, entities, raw_text, intent)
        
        # 2. Check Plugins
        else: 
            plugin_routed = False
            for plugin_name, plugin_instance in self.plugins.items():
                if plugin_instance.supports_intent(intent):
                    base_reply = await plugin_instance.execute_command(raw_text, parsed_command)
                    plugin_routed = True
                    break
            
            if not plugin_routed:
                base_reply = format_error_message(
                    f"I understood the intent '{intent}', but I lack the specific tool to execute it directly."
                )
        
        # 3. Stylize (Gemini)
        final_reply = base_reply
        if self.personality_enabled and base_reply and self.current_persona:
            system_instruction_for_gemini = ( 
                f"{self.current_persona.system_prompt()}\n"
                f"Respond in a {self.current_tone} tone. Keep the response suitable for robotic speech."
            )
            final_reply = await stylize_with_gemini(system_instruction_for_gemini, base_reply, raw_text) 
        
        return final_reply

    async def _handle_intent_with_error_handling(
        self, 
        handler: Callable, 
        entities: Dict[str, Any], 
        raw_command: str, 
        intent_name: str
    ) -> str:
        """Execute intent handler with error handling"""
        try:
            return await handler(entities, raw_command)
        except Exception as e:
            logger.error(
                f"Error executing handler for intent '{intent_name}'.",
                exc_info=True
            )
            return format_error_message(
                f"I had trouble processing your request concerning '{intent_name}'."
            )

    # --- Simple Internal Intent Handlers ---

    async def _handle_change_personality(self, entities: Dict[str, Any], raw_command: str) -> str:
        """Change the current personality"""
        new_persona_name_key = entities.get("persona_name", "").lower()
        if new_persona_name_key in self.personalities:
            self.current_persona = self.personalities[new_persona_name_key]
            self.current_tone = self.current_persona.tone
            logger.info(f"Personality changed to: {self.current_persona.name}")
            return f"Okay, I've switched my personality to {self.current_persona.name}."
        else:
            available_personas = ", ".join([p.name for p in self.personalities.values()])
            return f"Sorry, I don't have a personality named '{entities.get('persona_name')}'. Available: {available_personas}."

    async def _handle_change_tone(self, entities: Dict[str, Any], raw_command: str) -> str:
        """Change the current tone"""
        new_tone = entities.get("tone_name", "").strip()
        if new_tone:
            self.current_tone = new_tone
            logger.info(f"Tone changed to: {self.current_tone}")
            return f"Alright, I'll try to adopt a {self.current_tone} tone."
        return "What tone would you like me to use?"
    
    async def _handle_set_reminder(self, entities: Dict[str, Any], raw_command: str) -> str:
        """Set up a reminder"""
        note = entities.get("note")
        time_str = entities.get("time_str")
        if not note or not time_str:
            return "To set a reminder, I need the reminder text and a specific time."
        
        return self.modules_facade.user_reminder_service.setup_reminder(
            message=note, 
            time_str=time_str
        )

    async def _handle_tell_time(self, entities: Dict[str, Any], raw_command: str) -> str:
        """Tell the current time"""
        return self.modules_facade.time_utils.tell_time()

    async def _handle_tell_date(self, entities: Dict[str, Any], raw_command: str) -> str:
        """Tell the current date"""
        return self.modules_facade.time_utils.tell_date()