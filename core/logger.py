# core/logger.py
import logging
import time 
import os
from logging.handlers import RotatingFileHandler
from core.settings import settings # Import after settings is defined


# Configure the global logger for GENESIS
log_file_path = settings.get_log_file_path() 


# Ensure data directory for log file exists
log_dir = os.path.dirname(log_file_path)
if not os.path.exists(log_dir):
    try:
        os.makedirs(log_dir, exist_ok=True)
    except OSError as e:
        print(f"CRITICAL: Could not create log directory '{log_dir}': {e}")


# Define handlers
file_handler = RotatingFileHandler(
    log_file_path,
    maxBytes=settings.log_max_bytes,       
    backupCount=settings.log_backup_count, 
    encoding='utf-8'
)
stream_handler = logging.StreamHandler()


# Custom formatter for UTC time
class UTCFormatter(logging.Formatter): 
    converter = time.gmtime


formatter = UTCFormatter(
    fmt="%(asctime)s.%(msecs)03dZ [%(levelname)-8s] [%(name)s:%(module)s:%(lineno)d] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S" 
)


file_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)


# Configure basicConfig
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO), 
    handlers=[
        file_handler,
        stream_handler
    ]
)


logger = logging.getLogger("GENESIS")


# Silence overly-noisy 3rd-party logs (keep these as they are good practice)
logging.getLogger("aiocache").setLevel(logging.WARNING)
logging.getLogger("aiohttp").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING) 
logging.getLogger("PIL.PngImagePlugin").setLevel(logging.WARNING) 
logging.getLogger("matplotlib").setLevel(logging.WARNING) 
# Removed: logging.getLogger("speech_recognition").setLevel(logging.INFO) # No longer used
# Removed: logging.getLogger("pydub.utils").setLevel(logging.WARNING) # No longer used


logger.info(f"GENESIS Logger initialized. Level: {settings.log_level}. Logging to console and file: {log_file_path}")