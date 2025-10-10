# core/plugin_loader.py
import os
import importlib.util
import importlib.metadata
from typing import Dict, Any, Type, Optional

from core.logger import logger
from core.settings import settings
from core.plugin_interface import Plugin

def load_plugins(shared_resources: Dict[str, Any]) -> Dict[str, Plugin]:
    """
    Dynamically load plugins.
    1. Tries to load plugins via Python entry points under the "genesis.plugins" group.
    2. If no entry points are found or fail, falls back to loading from the legacy plugin directory.
    Injects shared_resources into plugin instances if they declare requirements.
    """
    plugins: Dict[str, Plugin] = {}
    entry_point_plugins_loaded_count = 0

    # 1. Load plugins from entry points
    logger.info("Attempting to load plugins via entry points (group 'genesis.plugins')...")
    try:
        entry_points = importlib.metadata.entry_points()
        genesis_plugin_eps = entry_points.select(group="genesis.plugins") if hasattr(entry_points, 'select') else entry_points.get("genesis.plugins", [])

        for ep in genesis_plugin_eps:
            plugin_instance_ep: Optional[Plugin] = None
            required_res_names_log = "N/A"
            try:
                loaded_object = ep.load()

                if isinstance(loaded_object, type) and issubclass(loaded_object, Plugin):
                    PluginClass_ep = loaded_object
                    required_res_names = PluginClass_ep.get_required_resources()
                    required_res_names_log = ", ".join(required_res_names) if required_res_names else "None"
                    resources_for_plugin = {name: res for name, res in shared_resources.items() if name in required_res_names}
                    plugin_instance_ep = PluginClass_ep(shared_resources=resources_for_plugin)
                elif isinstance(loaded_object, Plugin):
                    plugin_instance_ep = loaded_object
                    # For pre-instantiated plugins, resource injection depends on how they were created.
                    # We assume they handled it, or don't require injection via this loader.
                    required_res_names_log = "Pre-instantiated" 
                else:
                    logger.warning(f"Entry point '{ep.name}' loaded an object of type {type(loaded_object)}, not a Plugin class or instance. Skipping.")
                    continue
                
                if plugin_instance_ep:
                    if plugin_instance_ep.name in plugins:
                        logger.warning(f"Duplicate plugin name '{plugin_instance_ep.name}' from entry point '{ep.name}'. Overwriting.")
                    plugins[plugin_instance_ep.name] = plugin_instance_ep
                    logger.info(f"Loaded Plugin via entry point: {plugin_instance_ep.name} ({plugin_instance_ep.description}) from '{ep.module}'. Required resources: {required_res_names_log}")
                    entry_point_plugins_loaded_count += 1
            except Exception as e:
                logger.error(f"Failed to load plugin from entry point '{ep.name}'.", extra={"entry_point": ep.name, "error": str(e)}, exc_info=True)
    except Exception as e_outer:
        logger.error(f"Error accessing or processing entry points for 'genesis.plugins'.", extra={"error": str(e_outer)}, exc_info=True)

    # 2. Fallback: Load from legacy plugin directory if no entry point plugins were loaded
    if entry_point_plugins_loaded_count == 0:
        logger.info("No plugins loaded via entry points. Falling back to legacy file-based loading from directory.")
        plugin_dir_path = settings.get_plugin_dir_path()

        if not os.path.exists(plugin_dir_path) or not os.path.isdir(plugin_dir_path):
            logger.warning(f"Legacy plugin directory '{plugin_dir_path}' not found or not a directory. Skipping file-based loading.")
            return plugins

        for filename in os.listdir(plugin_dir_path):
            if filename.endswith(".py") and not filename.startswith("__"):
                module_name_fs = filename[:-3]
                module_path_fs = os.path.join(plugin_dir_path, filename)
                plugin_instance_fs: Optional[Plugin] = None
                required_res_names_log_fs = "N/A"
                try:
                    spec = importlib.util.spec_from_file_location(module_name_fs, module_path_fs)
                    if not (spec and spec.loader):
                        logger.error(f"Could not create import spec for module: {module_path_fs}")
                        continue
                    
                    module_fs = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module_fs)

                    PluginClass_file: Optional[Type[Plugin]] = getattr(module_fs, "PluginClass", None)
                    plugin_instance_direct: Optional[Plugin] = getattr(module_fs, "plugin_instance", # Changed from "plugin" to "plugin_instance" for clarity
                                                                          getattr(module_fs, "plugin", None)) 

                    if plugin_instance_direct and isinstance(plugin_instance_direct, Plugin):
                        plugin_instance_fs = plugin_instance_direct
                        required_res_names_log_fs = "Pre-instantiated"
                    elif PluginClass_file and isinstance(PluginClass_file, type) and issubclass(PluginClass_file, Plugin):
                        required_res_names_fs = PluginClass_file.get_required_resources()
                        required_res_names_log_fs = ", ".join(required_res_names_fs) if required_res_names_fs else "None"
                        resources_for_plugin_fs = {name: res for name, res in shared_resources.items() if name in required_res_names_fs}
                        plugin_instance_fs = PluginClass_file(shared_resources=resources_for_plugin_fs)
                    
                    if plugin_instance_fs:
                        if plugin_instance_fs.name in plugins:
                            logger.warning(f"Duplicate plugin name '{plugin_instance_fs.name}' found in legacy file {module_name_fs}. Overwriting existing plugin (possibly from entry point).")
                        plugins[plugin_instance_fs.name] = plugin_instance_fs
                        logger.info(f"Loaded Plugin (legacy file): {plugin_instance_fs.name} ({plugin_instance_fs.description}) from {module_name_fs}. Required resources: {required_res_names_log_fs}")
                    else:
                        logger.warning(
                            f"Module {module_name_fs} in legacy plugin directory does not export a 'PluginClass' inheriting "
                            f"from core.plugin_interface.Plugin, or a 'plugin_instance'/'plugin' instance. Plugin not loaded."
                        )
                except Exception as e_fs:
                    logger.error(f"Failed to load legacy plugin {module_name_fs} from {module_path_fs}.", extra={"module": module_name_fs, "error": str(e_fs)}, exc_info=True)
    
    if not plugins:
        logger.info("No plugins were loaded (neither entry points nor legacy files found/succeeded).")
    else:
        logger.info(f"Total plugins loaded: {len(plugins)} ({', '.join(plugins.keys())})")
    return plugins
