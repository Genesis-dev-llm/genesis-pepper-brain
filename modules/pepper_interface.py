# modules/pepper_interface.py
import asyncio
import threading
import time
from typing import Optional, Callable, Any, Dict, List, TYPE_CHECKING
from core.logger import logger

# Try to import NAOqi/qi libraries
try:
    import qi 
    from naoqi import ALProxy 
    NAOQI_AVAILABLE = True
except ImportError:
    qi = None
    ALProxy = None
    NAOQI_AVAILABLE = False
    logger.warning("NAOqi/qi library not found. PepperInterface running in MOCK mode.")

if TYPE_CHECKING:
    class ALTextToSpeechProxy:
        def say(self, text: str) -> None: ...
    class ALMotionProxy:
        def goToPosture(self, posture: str, speed: float) -> None: ...
        def getPosture(self) -> str: ...
    class ALMemoryProxy:
        def getData(self, key: str) -> Any: ...
        def subscribeToEvent(self, event_name: str, module_name: str, callback_method: str) -> None: ...
        def getEventList(self) -> List[str]: ...

class PepperInterface:
    """
    Manages connection, communication, and event subscription with Pepper robot.
    Wraps synchronous NAOqi SDK calls into asynchronous methods.
    """
    def __init__(self, ip: str, port: int):
        self.ip = ip
        self.port = port
        self.is_connected = False
        
        # NAOqi Session and Proxies
        self.session: Optional[qi.Session] = None
        self.tts_proxy: Optional['ALTextToSpeechProxy'] = None
        self.motion_proxy: Optional['ALMotionProxy'] = None
        self.memory_proxy: Optional['ALMemoryProxy'] = None
        
        # Event handling
        self.loop = asyncio.get_event_loop()
        self.callback_handler: Optional[Callable] = None
        self._sensor_thread: Optional[threading.Thread] = None
        self._stop_sensors = threading.Event()

    async def connect_async(self) -> bool:
        """Establishes the NAOqi session connection."""
        if not NAOQI_AVAILABLE:
            logger.warning("NAOqi not available. Running in MOCK mode for testing.")
            # For testing without a robot:
            self.is_connected = True
            return True

        logger.info(f"Attempting to connect to Pepper at {self.ip}:{self.port}...")
        
        def _connect_sync():
            try:
                session = qi.Session()
                session.connect(f"tcp://{self.ip}:{self.port}")
                
                # Get Proxies
                tts_proxy = session.service("ALTextToSpeech")
                motion_proxy = session.service("ALMotion")
                memory_proxy = session.service("ALMemory")
                
                return session, tts_proxy, motion_proxy, memory_proxy
            except Exception as e:
                logger.error(f"NAOqi connection failed: {e}", exc_info=True)
                return None, None, None, None

        session, tts_proxy, motion_proxy, memory_proxy = await self.loop.run_in_executor(
            None, _connect_sync
        )
        
        if session:
            self.session = session
            self.tts_proxy = tts_proxy
            self.motion_proxy = motion_proxy
            self.memory_proxy = memory_proxy
            self.is_connected = True
            logger.info("NAOqi connection established and proxies acquired.")
            return True
        
        logger.error("Failed to establish NAOqi connection.")
        return False

    async def disconnect_async(self):
        """Closes the NAOqi session."""
        if not self.is_connected:
            return
        
        logger.info("Disconnecting from Pepper...")
        
        # Stop sensor polling
        if self._sensor_thread and self._sensor_thread.is_alive():
            self._stop_sensors.set()
            self._sensor_thread.join(timeout=5)
        
        def _disconnect_sync():
            if self.session and hasattr(self.session, 'isConnected'):
                if self.session.isConnected():
                    self.session.close()
        
        try:
            await self.loop.run_in_executor(None, _disconnect_sync)
            self.is_connected = False
            logger.info("Successfully disconnected from Pepper.")
        except Exception as e:
            logger.warning(f"Error during NAOqi disconnection: {e}")

    # --- Actuator Commands (Asynchronous Wrappers) ---

    async def speak_async(self, text: str, animation: bool = True) -> None:
        """Uses ALTextToSpeech to speak text."""
        if not self.is_connected:
            logger.warning(f"Cannot speak in disconnected mode: '{text[:30]}...'")
            return
        
        if not self.tts_proxy:
            logger.info(f"[MOCK SPEAK]: {text}")
            return
        
        def _speak_sync():
            try:
                if animation:
                    self.tts_proxy.say(f"\\rspd=80\\ {text}")
                else:
                    self.tts_proxy.say(text)
            except Exception as e:
                logger.error(f"Error during Pepper speak command: {e}", exc_info=True)
                
        await self.loop.run_in_executor(None, _speak_sync)

    async def move_posture_async(self, posture: str = "Stand", speed: float = 0.8) -> None:
        """Wrapper for ALMotion.goToPosture."""
        if not self.is_connected or not self.motion_proxy:
            logger.debug(f"Cannot move in disconnected mode: posture={posture}")
            return
        
        def _move_sync():
            try:
                self.motion_proxy.goToPosture(posture, speed)
            except Exception as e:
                logger.error(f"Error during Pepper move command: {e}", exc_info=True)

        await self.loop.run_in_executor(None, _move_sync)

    # --- Sensor Subscription (Input Management) ---
    
    async def subscribe_to_all_sensors(
        self, 
        callback_handler: Callable[[Dict[str, Any]], None]
    ) -> None:
        """
        Subscribes to all necessary NAOqi events and sets the callback handler.
        Uses polling approach for simplicity and reliability.
        """
        if not self.is_connected:
            logger.warning("NAOqi connection required to subscribe to sensors.")
            return
        
        if not self.memory_proxy:
            logger.warning("Memory proxy not available. Sensor subscription skipped.")
            return

        self.callback_handler = callback_handler
        
        # Start sensor polling thread
        self._stop_sensors.clear()
        self._sensor_thread = threading.Thread(
            target=self._poll_sensors,
            daemon=True,
            name="PepperSensorThread"
        )
        self._sensor_thread.start()
        logger.info("Sensor polling thread started.")

    def _poll_sensors(self):
        """Background thread to poll sensors (synchronous)"""
        events_to_monitor = [
            "WordRecognized",
            "ALTextToSpeech/TextDone",
            "TouchChanged",
            "FrontTactilTouched",
            "MiddleTactilTouched",
            "RearTactilTouched"
        ]
        
        logger.info("Sensor polling active...")
        
        while not self._stop_sensors.is_set() and self.is_connected:
            try:
                for event_name in events_to_monitor:
                    try:
                        if not self.memory_proxy:
                            break
                        
                        value = self.memory_proxy.getData(event_name)
                        
                        # Only process meaningful events
                        if value and self._is_meaningful_event(event_name, value):
                            data = {
                                "event_name": event_name,
                                "value": value,
                                "timestamp": time.time()
                            }
                            
                            # Schedule callback in main event loop
                            asyncio.run_coroutine_threadsafe(
                                self._async_callback_wrapper(data),
                                self.loop
                            )
                    
                    except Exception as e:
                        logger.debug(f"Error polling {event_name}: {e}")
                
                # Poll frequency
                time.sleep(0.1)
            
            except Exception as e:
                logger.error(f"Error in sensor polling loop: {e}", exc_info=True)
                time.sleep(1)  # Back off on errors
        
        logger.info("Sensor polling stopped.")

    def _is_meaningful_event(self, event_name: str, value: Any) -> bool:
        """Filter out noise from sensor events"""
        if event_name == "WordRecognized":
            # Value is typically [text, confidence]
            if isinstance(value, list) and len(value) > 0:
                text = str(value[0]).strip()
                return len(text) > 0
        
        elif "Touched" in event_name or "TouchChanged" in event_name:
            # Touch events: value 1 = pressed, 0 = released
            return value == 1 or (isinstance(value, list) and 1 in value)
        
        elif "TextDone" in event_name:
            # TTS completion event
            return value == 1
        
        return bool(value)

    async def _async_callback_wrapper(self, data: Dict[str, Any]) -> None:
        """Wrapper to call the registered callback in async context"""
        if self.callback_handler:
            try:
                if asyncio.iscoroutinefunction(self.callback_handler):
                    await self.callback_handler(data)
                else:
                    self.callback_handler(data)
            except Exception as e:
                logger.error(f"Error in sensor callback handler: {e}", exc_info=True)