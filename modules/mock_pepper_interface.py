# modules/mock_pepper_interface.py
"""
Mock implementation of PepperInterface for testing without a physical robot.
Useful for development and CI/CD environments.
"""
import asyncio
import time
from typing import Optional, Callable, Any, Dict
from core.logger import logger

class MockPepperInterface:
    """
    Mock Pepper interface that simulates robot behavior without NAOqi connection.
    Logs all commands to console for debugging.
    """
    def __init__(self, ip: str, port: int):
        self.ip = ip
        self.port = port
        self.is_connected = False
        self.callback_handler: Optional[Callable] = None
        self._mock_events_active = False
        
        logger.info(f"MockPepperInterface initialized for {ip}:{port}")

    async def subscribe_to_all_sensors(
        self, 
        callback_handler: Callable[[Dict[str, Any]], None]
    ) -> None:
        """
        Simulate sensor subscription.
        Optionally generates mock sensor events for testing.
        """
        if not self.is_connected:
            logger.warning("[MOCK] Cannot subscribe to sensors - not connected.")
            return
        
        self.callback_handler = callback_handler
        logger.info("[MOCK] Subscribed to sensors (simulated).")
        
        # Optionally start generating mock events for testing
        # Uncomment the line below to enable mock event generation
        # asyncio.create_task(self._generate_mock_events())

    async def _generate_mock_events(self):
        """
        Generate mock sensor events for testing dialogue flow.
        This is useful for testing without manual input.
        """
        self._mock_events_active = True
        await asyncio.sleep(3)  # Wait a bit after startup
        
        # Example test phrases
        test_phrases = [
            "Hello Genesis",
            "What time is it?",
            "Tell me a joke",
            "Set a reminder for 3pm to call mom",
        ]
        
        phrase_index = 0
        
        while self._mock_events_active and self.is_connected:
            # Generate a mock speech recognition event
            if self.callback_handler and phrase_index < len(test_phrases):
                mock_event = {
                    "event_name": "WordRecognized",
                    "value": [test_phrases[phrase_index], 0.95],  # [text, confidence]
                    "timestamp": time.time()
                }
                
                logger.info(f"[MOCK EVENT] Generating: {test_phrases[phrase_index]}")
                
                # Call the registered callback
                if asyncio.iscoroutinefunction(self.callback_handler):
                    await self.callback_handler(mock_event)
                else:
                    self.callback_handler(mock_event)
                
                phrase_index += 1
            
            # Wait before next event
            await asyncio.sleep(10)
        
        logger.info("[MOCK] Event generation stopped.")

    def enable_mock_events(self):
        """Enable automatic mock event generation for testing"""
        if self.is_connected and not self._mock_events_active:
            asyncio.create_task(self._generate_mock_events())
            logger.info("[MOCK] Mock event generation enabled.")
        else:
            logger.warning("[MOCK] Cannot enable mock events - not connected or already active.") connect_async(self) -> bool:
        """Simulate connection to Pepper"""
        logger.info(f"[MOCK] Connecting to Pepper at {self.ip}:{self.port}...")
        await asyncio.sleep(0.5)  # Simulate connection delay
        self.is_connected = True
        logger.info("[MOCK] Connection established (simulated).")
        return True

    async def disconnect_async(self):
        """Simulate disconnection"""
        if not self.is_connected:
            return
        
        logger.info("[MOCK] Disconnecting from Pepper...")
        self._mock_events_active = False
        await asyncio.sleep(0.2)
        self.is_connected = False
        logger.info("[MOCK] Disconnected.")

    async def speak_async(self, text: str, animation: bool = True) -> None:
        """Simulate robot speech"""
        if not self.is_connected:
            logger.warning(f"[MOCK] Cannot speak - not connected: '{text[:30]}...'")
            return
        
        anim_str = " (with animation)" if animation else ""
        logger.info(f"[MOCK SPEAK{anim_str}]: {text}")
        
        # Simulate speech duration (roughly 0.1s per word)
        word_count = len(text.split())
        speech_duration = word_count * 0.1
        await asyncio.sleep(min(speech_duration, 3.0))  # Cap at 3 seconds

    async def move_posture_async(self, posture: str = "Stand", speed: float = 0.8) -> None:
        """Simulate robot movement"""
        if not self.is_connected:
            logger.debug(f"[MOCK] Cannot move - not connected: posture={posture}")
            return
        
        logger.info(f"[MOCK MOVE]: Posture={posture}, Speed={speed}")
        await asyncio.sleep(0.5)  # Simulate movement time

    async def