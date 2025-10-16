# modules/__init__.py
from .database import Database
from .task_manager import TaskManager
from .nlp_processor import NLPProcessor
from .reminder import ReminderService
from .response_formatter import format_error_message
from .sentiment import Sentiment
from .time_func import TimeFunctionality
from .confirmation import generate_confirmation
from .pepper_interface import PepperInterface
from .external_ai import ExternalAI
from .decision_engine import DecisionEngine
# The empty sub-folders will have their own __init__.py files

__all__ = [
    "database", "nlp_processor", "reminder", "response_formatter", "sentiment", 
    "task_manager", "time_func", "confirmation",
    "pepper_interface", "external_ai", "decision_engine"
]