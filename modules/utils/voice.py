# modules/utils/voice.py
"""
DEPRECATED: Synchronous voice utilities. 
I/O is now managed by the PepperInterface and NAOqi modules.
Kept as a file stub to match the directory structure plan.
"""
from core.settings import settings 
from core.logger import logger
from typing import Optional

# Removed pyttsx3, speech_recognition imports


def speak(text: str) -> None:
    """
    (DEPRECATED) Uses synchronous local TTS. 
    Prefer pepper_interface.speak_async(text).
    """
    logger.warning(f"Deprecated sync speak called: '{text[:50]}...'. Ignoring.")
    # In a full refactor, this would raise NotImplementedError.


def listen(timeout: int = 5, phrase_time_limit: int = 7) -> str:
    """
    (DEPRECATED) Uses synchronous local STT. 
    Input is managed via PepperInterface callbacks.
    """
    logger.warning("Deprecated sync listen called. Ignoring.")
    return ""