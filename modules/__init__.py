# modules/__init__.py

# Explicitly import all top-level modules so Python recognizes them immediately
from . import database
from . import nlp_processor
from . import reminder
from . import response_formatter
from . import sentiment
from . import task_manager
from . import time_func
from . import confirmation

# Also import the new modules
from . import pepper_interface
from . import external_ai
from . import decision_engine

# You can optionally list sub-packages here too, although they should be auto-discovered
from . import dialogue
from . import personalities

__all__ = [
    "database", "nlp_processor", "reminder", "response_formatter", "sentiment", 
    "task_manager", "time_func", "confirmation",
    "pepper_interface", "external_ai", "decision_engine"
]