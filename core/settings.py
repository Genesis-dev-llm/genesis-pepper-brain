# core/settings.py
import os
import ipaddress
from typing import List, Dict, Union, Any, Literal, Optional 
from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # --- PEPPER Robot Connection ---
    pepper_ip: str = Field(..., env='PEPPER_IP', min_length=7)
    pepper_port: int = Field(9559, env='PEPPER_PORT', gt=0)

    # --- REQUIRED External AI Keys ---
    gemini_api_key: SecretStr = Field(..., env='GEMINI_API_KEY')

    # --- User Preferences ---
    language: str = Field('en-US', env='LANGUAGE') 
    personality: str = Field("genesis", env="PERSONALITY") 
    use_gemini_styling: bool = Field(True, env='USE_GEMINI_STYLING') 

    # --- NLP Settings ---
    spacy_model: str = Field("en_core_web_sm", env="SPACY_MODEL")
    
    # --- File Paths & Data Configuration ---
    data_dir_name: str = Field("data", env="DATA_DIR_NAME") 
    
    log_file_name: str = Field("genesis.log", env="LOG_FILE_NAME")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field("INFO", env="LOG_LEVEL") 
    log_max_bytes: int = Field(5*1024*1024, env="LOG_MAX_BYTES", gt=0) 
    log_backup_count: int = Field(3, env="LOG_BACKUP_COUNT", ge=0) 
    
    interactions_log_file_name: str = Field("interactions.log", env="INTERACTIONS_LOG_FILE_NAME")
    database_file_name: str = Field("genesis.db", env="DATABASE_FILE_NAME")
    memory_file_name: str = Field("memory.json", env="MEMORY_FILE_NAME")
    plugin_dir_name: str = Field("plugins", env="PLUGIN_DIR_NAME") 

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_file_encoding='utf-8')

    @field_validator('pepper_ip')
    @classmethod
    def validate_ip(cls, v: str) -> str:
        """Validate IP address format or allow hostname"""
        try:
            ipaddress.ip_address(v)
            return v
        except ValueError:
            # Allow hostnames
            if not v or len(v) < 3:
                raise ValueError("Invalid PEPPER_IP: must be valid IP address or hostname")
            return v

    @property
    def project_root_dir(self) -> str:
        """Calculate project root relative to this file"""
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    def get_data_path(self, filename: Optional[str] = None) -> str:
        path = os.path.join(self.project_root_dir, self.data_dir_name)
        if filename:
            return os.path.join(path, filename)
        return path

    def get_db_path(self) -> str:
        return self.get_data_path(self.database_file_name)

    def get_log_file_path(self) -> str:
        return self.get_data_path(self.log_file_name)

    def get_interactions_log_path(self) -> str:
        return self.get_data_path(self.interactions_log_file_name)

    def get_memory_file_path(self) -> str:
        return self.get_data_path(self.memory_file_name)
        
    def get_plugin_dir_path(self) -> str: 
        return os.path.join(self.project_root_dir, self.plugin_dir_name)

    @model_validator(mode='after')
    def _validate_paths(self) -> 'Settings':
        self.ensure_data_dir_exists()
        return self

    def ensure_data_dir_exists(self):
        full_data_dir_path = self.get_data_path()
        if not os.path.exists(full_data_dir_path):
            try:
                os.makedirs(full_data_dir_path, exist_ok=True)
                print(f"Data directory '{full_data_dir_path}' created/ensured.")
            except OSError as e:
                print(f"Critical Error: Could not create data directory '{full_data_dir_path}': {e}")
                raise 

settings = Settings()