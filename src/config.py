"""
Configuration loader for the cold email agent.
Loads settings from YAML file and environment variables.
"""

import os
import yaml
from typing import Any, Dict, Optional
from dotenv import load_dotenv
from pathlib import Path


class Config:
    """Configuration manager."""
    
    def __init__(self, config_file: str = "config/config.yaml"):
        """
        Initialize configuration.
        
        Args:
            config_file: Path to YAML config file
        """
        # Load environment variables from .env file
        load_dotenv()
        
        self.config_file = config_file
        self.config: Dict[str, Any] = {}
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        if not os.path.exists(self.config_file):
            raise FileNotFoundError(f"Config file not found: {self.config_file}")
        
        with open(self.config_file, 'r') as f:
            self.config = yaml.safe_load(f) or {}
        
        # Substitute environment variables
        self._substitute_env_vars()
    
    def _substitute_env_vars(self) -> None:
        """Replace ${VAR_NAME} with environment variable values."""
        def substitute_dict(d: Dict) -> None:
            for key, value in d.items():
                if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                    env_var = value[2:-1]
                    d[key] = os.getenv(env_var, value)
                elif isinstance(value, dict):
                    substitute_dict(value)
        
        substitute_dict(self.config)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-notation key.
        Example: 'smtp.sender_email' returns config['smtp']['sender_email']
        
        Args:
            key: Dot-notation configuration key
            default: Default value if key not found
        
        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any) -> None:
        """Set a configuration value by dot-notation key."""
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def validate_required_fields(self) -> bool:
        """Validate that required fields are set."""
        required = [
            ('smtp.sender_email', 'SMTP sender email'),
            ('smtp.app_password', 'SMTP app password'),
            ('ai.api_key', 'OpenAI API key'),
        ]
        
        missing = []
        for key, description in required:
            if not self.get(key):
                missing.append(f"{description} ({key})")
        
        if missing:
            print("\n⚠️  Missing required configuration:")
            for item in missing:
                print(f"  - {item}")
            return False
        
        return True
    
    def __repr__(self) -> str:
        """String representation of config (safe, hides secrets)."""
        return f"<Config from {self.config_file}>"


# Global config instance
_config_instance: Optional[Config] = None


def get_config(config_file: str = "config/config.yaml") -> Config:
    """Get or create global config instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config(config_file)
    return _config_instance


def reset_config() -> None:
    """Reset global config instance (for testing)."""
    global _config_instance
    _config_instance = None
