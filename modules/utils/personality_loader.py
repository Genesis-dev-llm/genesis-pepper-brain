# modules/utils/personality_loader.py
import pkgutil
import importlib
import inspect
from types import SimpleNamespace
from core.logger import logger
from core.settings import settings
from modules.personalities.profile import PersonaProfile
from typing import Dict

PERSONALITIES_PACKAGE_PATH = "modules.personalities" 

def load_personalities() -> SimpleNamespace:
    """
    Discovers and loads all PersonaProfile objects defined in modules
    under the 'modules.personalities' package.
    Returns a SimpleNamespace where attributes are PersonaProfile instances.
    """
    personas_map: Dict[str, PersonaProfile] = {}
    logger.info(f"Loading personas from package: {PERSONALITIES_PACKAGE_PATH}")

    try:
        # Dynamically import the personalities package
        package = importlib.import_module(PERSONALITIES_PACKAGE_PATH)
        
        # Get package paths
        package_paths = package.__path__ if hasattr(package, '__path__') else []

        for path_item in package_paths:
            for _, modname, ispkg in pkgutil.iter_modules([path_item], package.__name__ + "."):
                if ispkg:
                    logger.debug(f"Skipping sub-package {modname} during persona loading.")
                    continue
                
                try:
                    module = importlib.import_module(modname)
                    
                    # Look for PersonaProfile instances
                    for attr_name in dir(module):
                        if attr_name.startswith('_'):
                            continue
                        
                        attr_value = getattr(module, attr_name)
                        
                        if isinstance(attr_value, PersonaProfile):
                            profile_instance = attr_value
                            persona_key = profile_instance.name.lower()
                            
                            if persona_key in personas_map:
                                logger.warning(
                                    f"Duplicate persona name '{persona_key}' found in module '{modname}'. "
                                    f"Previous definition will be overwritten."
                                )
                            
                            personas_map[persona_key] = profile_instance
                            logger.info(
                                f"Loaded persona: '{profile_instance.name}' (key: '{persona_key}') "
                                f"from module '{modname}'. Tone: {profile_instance.tone}"
                            )
                
                except ImportError as e_import:
                    logger.error(
                        f"Failed to import persona module '{modname}'.",
                        extra={"module": modname, "error": str(e_import)}, 
                        exc_info=True
                    )
                except Exception as e_module:
                    logger.error(
                        f"Error processing persona module '{modname}'.",
                        extra={"module": modname, "error": str(e_module)}, 
                        exc_info=True
                    )

    except ImportError:
        logger.critical(
            f"Personalities package '{PERSONALITIES_PACKAGE_PATH}' not found. "
            f"No personas will be loaded.", 
            exc_info=True
        )
    except Exception as e_pkg:
        logger.critical(
            f"Error iterating personality modules in '{PERSONALITIES_PACKAGE_PATH}'.",
            extra={"error": str(e_pkg)}, 
            exc_info=True
        )

    # Create default fallback persona if none were loaded
    if not personas_map:
        logger.warning(
            "No persona profiles were loaded. "
            "Creating default fallback persona."
        )
        
        default_fallback = PersonaProfile(
            name="DefaultGenesis",
            tone="neutral",
            system_prompt_template="You are GENESIS, a helpful AI assistant.",
            language_code=settings.language
        )
        personas_map["defaultgenesis"] = default_fallback
        logger.info("Created and loaded minimal default persona ('DefaultGenesis') as fallback.")

    # Convert dict to SimpleNamespace for attribute access
    # Use the persona name (not the key) as the attribute name
    personas_ns_dict = {}
    for key, profile in personas_map.items():
        # Use the actual profile name (properly cased) as the attribute name
        attr_name = profile.name.replace(" ", "").replace("-", "_")
        personas_ns_dict[attr_name] = profile
    
    return SimpleNamespace(**personas_ns_dict)