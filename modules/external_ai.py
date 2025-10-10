# modules/external_ai.py
import asyncio
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from core.settings import settings
from core.logger import logger
from typing import Optional, Dict, Any, List

# --- Initialize Gemini Client ---
try:
    if settings.gemini_api_key and settings.gemini_api_key.get_secret_value():
        genai.configure(api_key=settings.gemini_api_key.get_secret_value())
        
        # Safety settings (properly formatted as dict)
        safety_settings_config = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        }
        
        # Generation config
        generation_config = genai.types.GenerationConfig(
            max_output_tokens=1024,
            temperature=0.75,
        )
        
        gemini_client = genai.GenerativeModel(
            'gemini-2.0-flash-exp',  # Updated to latest model
            safety_settings=safety_settings_config,
            generation_config=generation_config
        )
        logger.info("ExternalAI: Google Gemini client configured with model 'gemini-2.0-flash-exp'.")
    else:
        gemini_client = None
        logger.warning("ExternalAI: GEMINI_API_KEY not set. External AI services are disabled.")
except Exception as e:
    gemini_client = None
    logger.error(f"ExternalAI: Failed to configure Google Gemini client: {e}", exc_info=True)

class ExternalAI:
    @staticmethod
    async def get_general_response(
        system_prompt: str, 
        user_query: str, 
        history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Retrieves a conversational response from the Gemini model.
        Used for general knowledge queries and complex conversation flows.
        """
        if not gemini_client:
            return "I am currently disconnected from the external AI services."

        try:
            # Construct the full prompt with system instructions
            full_prompt = f"{system_prompt}\n\nUser: {user_query}\n\nAssistant:"
            
            # Run the synchronous generate_content call in a thread
            def _generate_sync():
                try:
                    response = gemini_client.generate_content(full_prompt)
                    if response and hasattr(response, 'text'):
                        return response.text.strip()
                    return None
                except Exception as e_inner:
                    logger.error(f"Error in Gemini generate_content: {e_inner}", exc_info=True)
                    return None
            
            response_text = await asyncio.to_thread(_generate_sync)
            
            if response_text:
                return response_text
            else:
                logger.warning(f"External AI returned empty or blocked response for query: {user_query[:50]}...")
                return "The external AI response was empty or filtered."

        except Exception as e:
            logger.error(f"Error accessing External AI service: {e}", exc_info=True)
            return "I am experiencing technical difficulties reaching the external AI brain."