# modules/dialogue/gemini_adapter.py
import asyncio
from core.settings import settings
from core.logger import logger
from typing import Optional

# NEW: Import the External AI gateway
from modules.external_ai import ExternalAI 


async def stylize_with_gemini(system_prompt: str, base_reply_content: str, original_user_query: Optional[str] = None) -> str: 
    """
    Styles the base_reply_content using Google Gemini based on the system_prompt (persona instructions)
    and original_user_query for context, using the ExternalAI gateway.
    Returns the styled text, or the base_reply_content on failure.
    """
    # NOTE: The ExternalAI class handles the client configuration and is pre-initialized.
    
    if not base_reply_content or not base_reply_content.strip():
        logger.debug("Stylizer called with empty base_reply_content. Returning as is.")
        return base_reply_content 

    # Construct the instruction for the LLM
    context_parts = [system_prompt]
    if original_user_query:
        context_parts.append(f"User's original query: \"{original_user_query}\"")
    
    context_parts.append(f"The system has generated the following CORE information to be stylized: \"{base_reply_content}\"")
    context_parts.append(f"Rephrase or style this core information according to your persona and tone. The final response will be spoken by a physical robot; keep it conversational and slightly concise.")
    
    full_styling_prompt = "\n\n".join(context_parts)
    
    log_extra = {"base_reply_start": base_reply_content[:100]}
    logger.debug("Sending request to External AI for styling.", extra=log_extra)

    try:
        # Use the ExternalAI gateway for the actual API call
        styled_text = await ExternalAI.get_general_response(
            system_prompt=system_prompt, # Re-using the prompt header
            user_query=full_styling_prompt
        )
        
        # Check if ExternalAI returned its own error message
        if styled_text and styled_text.startswith("I am currently disconnected"):
            logger.warning("External AI disconnected. Using base reply.")
            return base_reply_content
        
        logger.info(f"External AI styled response received (length: {len(styled_text)}).", extra=log_extra)
        return styled_text
        
    except Exception as e_gemini:
        logger.warning(f"External AI styling failed: {e_gemini}. Using base reply.", exc_info=True)
        return base_reply_content