# modules/decision_engine.py
from typing import Dict, Any, Optional, TYPE_CHECKING
from core.logger import logger
import asyncio

if TYPE_CHECKING:
    from modules.pepper_interface import PepperInterface
    from modules.nlp_processor import NLPProcessor
    from types import SimpleNamespace
    from modules.dialogue.dialogue_manager import DialogueManager

class DecisionEngine:
    """
    Core logic for taking processed sensor input, determining the intent, 
    and formulating an appropriate, actionable response (speech + movement).
    """
    def __init__(
        self, 
        pepper_interface: 'PepperInterface',
        nlp_processor: 'NLPProcessor',
        modules_facade: 'SimpleNamespace',
        dialogue_manager: 'DialogueManager'
    ):
        self.pepper = pepper_interface
        self.nlp = nlp_processor
        self.facade = modules_facade
        self.dm = dialogue_manager
        logger.info("DecisionEngine initialized.")

    async def process_user_speech(self, user_text: str) -> str:
        """
        Handles the flow from user speech input to robot action.
        1. NLP Parsing
        2. Internal/External Decision Routing
        3. Action Planning
        4. Robot Execution (Speech/Motion)
        """
        
        # --- 1. NLP Parsing ---
        parsed_command = self.nlp.parse_command(user_text)
        intent = parsed_command.get("intent", "unknown")
        entities = parsed_command.get("entities", {})
        
        log_extra = {"intent": intent, "entities": entities}
        logger.info(f"DecisionEngine received speech, Intent: {intent}", extra=log_extra)
        
        # Initialize action plan and response
        action_plan = None
        response = ""
        
        # --- 2. Internal Routing (Simple Actions) ---
        
        # Example: Simple internal time/date checks
        if intent == "tell_time":
            response = self.facade.time_utils.tell_time()
            action_plan = {"speech": response, "motion": "HeadYaw:0"}
        
        elif intent == "tell_date":
            response = self.facade.time_utils.tell_date()
            action_plan = {"speech": response, "motion": "HeadYaw:0"}
        
        # Example: Direct Command
        elif intent == "change_personality":
            # Delegate to DialogueManager for complex flow
            response = await self.dm.process_turn(user_text) 
            action_plan = {"speech": response, "motion": "BodyLanguage:Joy"}
        
        elif intent == "set_reminder":
            # Delegate to DialogueManager
            response = await self.dm.process_turn(user_text)
            action_plan = {"speech": response, "motion": "HeadNod"}
        
        # --- 3. External Routing (Complex/General Queries) ---
        elif intent in ["unknown", "general_query"] or intent not in self.dm.intent_handlers:
            # Get persona context for the system prompt
            effective_persona = self.dm.current_persona
            effective_tone = self.dm.current_tone
            
            system_instruction = (
                f"{effective_persona.system_prompt()}\n"
                f"You are speaking through a physical robot named Pepper. Keep responses concise "
                f"and conversational. Respond in a {effective_tone} tone."
            )
            
            from modules.external_ai import ExternalAI
            
            # Send the query to the External LLM
            llm_response = await ExternalAI.get_general_response(
                system_instruction, 
                user_text
            )
            
            response = llm_response
            action_plan = {"speech": llm_response, "motion": "BodyLanguage:Think"}

        # --- 4. Action Planning & Execution ---
        if action_plan and response:
            try:
                # Execute speech
                speech_task = self.pepper.speak_async(action_plan['speech'])
                
                # Simple motion execution
                motion_task = None
                motion_cmd = action_plan.get('motion', '')
                
                if 'move_posture' in motion_cmd:
                    posture = motion_cmd.split(':')[1]
                    motion_task = self.pepper.move_posture_async(posture=posture)
                elif motion_cmd and motion_cmd != 'HeadYaw:0':
                    # Default motion for other cases
                    motion_task = self.pepper.move_posture_async(posture="Stand")
                
                # Wait for speech to complete (since speech defines end of turn)
                if motion_task:
                    await asyncio.gather(speech_task, motion_task)
                else:
                    await speech_task
                
                # Log the interaction
                self.dm.log_interaction(user_text, response)
                
                return response
            
            except Exception as e:
                logger.error(f"Error executing action plan: {e}", exc_info=True)
                return "I encountered an error while processing your request."
        
        # Fallback response
        fallback = "I'm not sure how to respond to that."
        await self.pepper.speak_async(fallback)
        return fallback