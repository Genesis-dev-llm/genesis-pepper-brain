# modules/utils/module_loader.py
import importlib
import pkgutil
import os
from types import SimpleNamespace
from core.logger import logger
from core.settings import settings

# Explicitly import known module classes/functions
from modules.database import Database
from modules.reminder import ReminderService
from modules.time_func import TimeFunctionality
from modules.sentiment import Sentiment as GeneralSentimentService
from modules.confirmation import generate_confirmation
from modules.response_formatter import ( 
    format_analyze_sentiment, 
    format_error_message
)

# New modules
from modules.pepper_interface import PepperInterface
from modules.external_ai import ExternalAI

from typing import TYPE_CHECKING, Any, Dict
if TYPE_CHECKING:
    from modules.database import Database
    from utils.memory_manager import MemoryManager
    from modules.task_manager import TaskManager

def load_modules_facade(
    db_instance: 'Database',
    memory_manager_instance: 'MemoryManager',
    task_manager_instance: 'TaskManager',
    pepper_interface_instance: 'PepperInterface'
) -> SimpleNamespace:
    """
    Creates a SimpleNamespace acting as a facade for core functional modules and services.
    Instantiates services requiring shared managers and dynamically loads other utility modules.
    """
    logger.info("Loading application modules facade...")

    # Instantiate services with dependencies
    user_reminder_service = ReminderService(
        task_manager=task_manager_instance,
        pepper_interface=pepper_interface_instance
    )

    modules_ns_dict: Dict[str, Any] = { 
        # --- Core Infrastructure/State ---
        "database": db_instance,
        "memory": memory_manager_instance,
        "task_manager": task_manager_instance,
        
        # --- Communication Layers ---
        "pepper_interface": pepper_interface_instance, 
        "external_ai": ExternalAI,  # Static methods class
        
        # --- Reusable Business Logic ---
        "user_reminder_service": user_reminder_service,
        "time_utils": TimeFunctionality,
        "general_sentiment": GeneralSentimentService,
        "confirmation_generator": generate_confirmation, 
        
        # --- Formatting ---
        "response_formatters": SimpleNamespace( 
            analyze_sentiment=format_analyze_sentiment,
            error_message=format_error_message
        ),
    }
    
    # Dynamic loading of additional modules
    modules_dir_path = os.path.join(settings.project_root_dir, "modules")
    excluded_module_names = {
        "database", "nlp_processor", "task_manager", "reminder",
        "pepper_interface", "external_ai", "decision_engine",
        "sentiment", "confirmation", "response_formatter", "dialogue", 
        "utils", "personalities", "time_func",
        "__init__", "__pycache__"
    }
    
    logger.debug(f"Scanning for additional dynamic modules in: {modules_dir_path}")
    
    if os.path.exists(modules_dir_path):
        for finder, name, ispkg in pkgutil.iter_modules([modules_dir_path]):
            if not name.startswith("__") and not ispkg and name not in excluded_module_names:
                try:
                    module_import_path = f"modules.{name}"
                    imported_module = importlib.import_module(module_import_path)
                    
                    # Use simplified name (without _service suffix)
                    module_key = name.replace("_service", "")
                    modules_ns_dict[module_key] = imported_module 
                    
                    logger.info(f"Dynamically loaded module '{name}' into facade.")
                except Exception as e:
                    logger.error(
                        f"Failed to dynamically load module '{name}'.",
                        extra={"module_name": name, "error": str(e)}, 
                        exc_info=True
                    )

    facade = SimpleNamespace(**modules_ns_dict)
    logger.info("Application modules facade loaded successfully with core services and utilities.")
    return facade