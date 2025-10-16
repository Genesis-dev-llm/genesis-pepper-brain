# main.py
import sys
import os 

# --- Path Fix for Local Module Discovery ---
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import asyncio
import time
import atexit
import signal
from types import SimpleNamespace
from typing import Dict, Optional, Any, List
from datetime import datetime, timezone 

# Core GENESIS imports
from core.settings import settings
from core.logger import logger 
from core.plugin_loader import load_plugins
from core.plugin_interface import Plugin

# --- MODULE/UTIL IMPORTS (Explicity list each needed component) ---
# NOTE: This list relies on the path fix to find 'modules' and 'utils' folders.
from modules.database import Database
from modules.task_manager import TaskManager
from modules.nlp_processor import NLPProcessor
from modules.dialogue.dialogue_manager import DialogueManager
from modules.pepper_interface import PepperInterface 
from utils.memory_manager import MemoryManager
from utils.module_loader import load_modules_facade 

# --- Global Component Instances ---
db: Optional[Database] = None
memory_mgr: Optional[MemoryManager] = None
nlp_proc: Optional[NLPProcessor] = None
task_mgr: Optional[TaskManager] = None
dialogue_mgr_instance: Optional[DialogueManager] = None
app_modules_facade: Optional[SimpleNamespace] = None
loaded_plugins: Dict[str, Plugin] = {}
pepper_interface: Optional[PepperInterface] = None 
plugin_background_tasks: List[asyncio.Task] = []

# For graceful shutdown
shutdown_event = asyncio.Event()

def signal_handler_fn(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Signal {signal.Signals(signum).name} received. Initiating graceful shutdown...")
    shutdown_event.set()

async def initialize_core_components(app_loop: Optional[asyncio.AbstractEventLoop] = None) -> bool:
    """Initializes all core modules and establishes connection to Pepper."""
    global db, memory_mgr, nlp_proc, task_mgr, dialogue_mgr_instance, app_modules_facade
    global loaded_plugins, pepper_interface, plugin_background_tasks
    
    logger.info("--- GENESIS v3.0 (Pepper Brain) Initializing Core Components ---")
    
    try:
        settings.ensure_data_dir_exists() 

        # Initialize core managers
        db = Database() 
        memory_mgr = MemoryManager() 
        nlp_proc = NLPProcessor() 
        
        # This check is valid, but Pylance warns nlp_proc could be None.
        # Let's add an assertion to satisfy the type checker.
        assert nlp_proc is not None
        if not nlp_proc.nlp: # Now Pylance knows nlp_proc is not None here.
            logger.critical("NLP model (spaCy) failed to load. Core NLP functionality will be impaired.")

        task_mgr = TaskManager()

        # 1. Initialize Pepper Interface (CRITICAL)
        pepper_interface = PepperInterface(
            ip=settings.pepper_ip, 
            port=settings.pepper_port
        )
        
        connection_success = await pepper_interface.connect_async()
        
        if not connection_success or not pepper_interface.is_connected:
            logger.critical(
                f"Failed to connect to Pepper at {settings.pepper_ip}:{settings.pepper_port}. "
                f"Check robot IP, port, and network connectivity."
            )
            return False

        # Prepare shared resources for plugins and modules
        current_loop = app_loop or asyncio.get_running_loop()
        shared_plugin_resources = {
            'db': db, 
            'task_manager': task_mgr,
            'pepper_interface': pepper_interface, 
            'settings': settings, 
            'main_loop': current_loop
        }
        
        loaded_plugins = load_plugins(shared_resources=shared_plugin_resources)
        
        # Initialize ModulesFacade
        app_modules_facade = load_modules_facade(
            db_instance=db, 
            memory_manager_instance=memory_mgr, 
            task_manager_instance=task_mgr,
            pepper_interface_instance=pepper_interface 
        )
        
        # Add assertions to assure the type checker these are not None
        assert nlp_proc is not None
        assert memory_mgr is not None
        assert app_modules_facade is not None
        assert pepper_interface is not None
        # Initialize DialogueManager (which creates DecisionEngine internally)
        dialogue_mgr_instance = await DialogueManager.create(
            nlp_processor=nlp_proc, 
            memory_manager=memory_mgr,
            modules_facade=app_modules_facade, 
            plugins_dict=loaded_plugins,
            pepper_interface=pepper_interface 
        )

        # 2. Execute plugin startup routines asynchronously
        if loaded_plugins:
            logger.info(f"Executing run() methods for {len(loaded_plugins)} loaded plugins...")
            for plugin_name, plugin_instance in loaded_plugins.items():
                try:
                    if asyncio.iscoroutinefunction(getattr(plugin_instance, 'run', None)): 
                        task = asyncio.create_task(plugin_instance.run())
                        task.set_name(f"plugin_{plugin_name}")
                        plugin_background_tasks.append(task)
                        logger.info(f"Scheduled async run() for plugin '{plugin_name}'.")
                    elif hasattr(plugin_instance, 'run'):
                        await current_loop.run_in_executor(None, plugin_instance.run)
                        logger.info(f"Executed sync run() for plugin '{plugin_name}' in executor.")
                except Exception as e_plugin_run:
                    logger.error(
                        f"Error executing run() for plugin '{plugin_name}'.",
                        extra={"plugin": plugin_name, "error": str(e_plugin_run)}, 
                        exc_info=True
                    )
        
        # 3. Register DialogueManager as the primary sensor callback handler
        # The callback must be a sync function that schedules the async handler.
        assert dialogue_mgr_instance is not None
        
        def sensor_callback_wrapper(sensor_data: Dict[str, Any]) -> None:
            """
            Synchronous wrapper to schedule the async callback handler on the event loop.
            This is required because the underlying library expects a sync callback.
            """
            if dialogue_mgr_instance:
                asyncio.create_task(dialogue_mgr_instance.handle_sensor_callback(sensor_data))

        await pepper_interface.subscribe_to_all_sensors(
            sensor_callback_wrapper
        )
        
        logger.info("--- GENESIS Core Components Initialized Successfully ---")
        return True
    
    except Exception as e:
        logger.critical(f"Critical error during core component initialization: {e}", exc_info=True)
        
        # Cleanup on failure
        if db and hasattr(db, 'close'):
            db.close()
        if task_mgr and hasattr(task_mgr, 'stop_scheduler_thread'):
            task_mgr.stop_scheduler_thread()
        if pepper_interface and pepper_interface.is_connected:
            asyncio.create_task(pepper_interface.disconnect_async())
        
        return False

def log_interaction(user_input: str, genesis_response: str): 
    """Appends interaction to interactions_log_file (from settings)."""
    try:
        ts = datetime.now(timezone.utc).isoformat()
        log_path = settings.get_interactions_log_path()
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"{ts} | User: {user_input}\n")
            f.write(f"{ts} | GENESIS: {genesis_response}\n\n")
    except Exception as e:
        logger.error(f"Error logging interaction to file '{log_path}': {e}", exc_info=False)

async def pepper_middleware_loop():
    """Main event loop - monitors connection and waits for shutdown"""
    global pepper_interface
    
    if not pepper_interface:
        logger.critical("Pepper Interface not initialized. Cannot start main loop.")
        return

    logger.info("GENESIS Pepper Middleware Loop started. Awaiting sensor callbacks...")
    
    # Send initial greeting
    initial_greeting = f"Hello. I am Genesis, the middleware brain. I am now connected to {pepper_interface.ip}."
    await pepper_interface.speak_async(initial_greeting)

    # Heartbeat monitoring loop
    heartbeat_interval = 5  # seconds
    last_check = time.time()
    
    while not shutdown_event.is_set():
        try:
            # Check connection health
            current_time = time.time()
            if current_time - last_check >= heartbeat_interval:
                if not pepper_interface.is_connected:
                    logger.error("Lost connection to Pepper. Attempting reconnect...")
                    reconnect_success = await pepper_interface.connect_async()
                    
                    if reconnect_success:
                        logger.info("Reconnected to Pepper successfully.")
                        # Re-subscribe to sensors
                        # The callback must be a sync function that schedules the async handler.
                        assert dialogue_mgr_instance is not None
                        
                        def sensor_callback_wrapper(sensor_data: Dict[str, Any]) -> None:
                            """
                            Synchronous wrapper to schedule the async callback handler on the event loop.
                            """
                            if dialogue_mgr_instance:
                                asyncio.create_task(dialogue_mgr_instance.handle_sensor_callback(sensor_data))

                        await pepper_interface.subscribe_to_all_sensors(
                            sensor_callback_wrapper
                        )
                    else:
                        logger.error("Reconnection failed. Will retry...")
                
                last_check = current_time
            
            # Short sleep to prevent busy-waiting
            await asyncio.sleep(1)
        
        except Exception as e:
            logger.error(f"Error in main loop: {e}", exc_info=True)
            await asyncio.sleep(5)  # Back off on errors

    logger.info("Pepper Middleware main loop ended.")

def cleanup_resources():
    """Cleanup function called on shutdown"""
    logger.info("--- GENESIS v3.0 Cleaning Up Resources ---")
    
    # Cancel plugin background tasks
    if plugin_background_tasks:
        logger.debug(f"Cancelling {len(plugin_background_tasks)} plugin tasks...")
        for task in plugin_background_tasks:
            if not task.done():
                task.cancel()
    
    if task_mgr and hasattr(task_mgr, 'stop_scheduler_thread'):
        logger.debug("Stopping TaskManager scheduler thread...")
        task_mgr.stop_scheduler_thread()
    
    if db and hasattr(db, 'close'):
        logger.debug("Closing database connection...")
        db.close()
    
    if pepper_interface and hasattr(pepper_interface, 'disconnect_async'):
        logger.debug("Disconnecting from Pepper...")
        try:
            asyncio.run(pepper_interface.disconnect_async())
        except Exception as e:
            logger.warning(f"Async disconnect failed in cleanup: {e}")
             
    logger.info("--- GENESIS Cleanup Complete ---")

def main_cli_entry():
    """Standard entry point for synchronous execution"""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application interrupted by user (Ctrl+C).")
    except Exception as e:
        logger.critical(f"Fatal error during synchronous startup: {e}", exc_info=True)
        sys.exit(1)

async def main(): 
    """Main async entry point"""
    components_ok = await initialize_core_components(app_loop=asyncio.get_event_loop())
    
    if not components_ok:
        logger.critical("GENESIS could not initialize critical components. Exiting application.")
        sys.exit(1)

    await pepper_middleware_loop()

if __name__ == "__main__":
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler_fn)
    if hasattr(signal, 'SIGTERM'): 
        signal.signal(signal.SIGTERM, signal_handler_fn)
    
    # Register cleanup function
    atexit.register(cleanup_resources)

    # Run the application
    main_cli_entry()