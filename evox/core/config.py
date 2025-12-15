"""
Configuration Management for Evox Framework

This module provides configuration management for the Evox framework,
including default settings for priority queues, caching, and other features.
"""

from typing import Dict, Any
import tomli
import os
from pathlib import Path


class ConfigManager:
    """
    Configuration manager for Evox framework.
    
    Manages framework configuration from various sources:
    1. Default built-in configuration
    2. config.toml files in project root
    3. Environment variables
    4. Runtime overrides
    
    Design Notes:
    - Follows convention over configuration principle
    - Provides sensible defaults for all settings
    - Supports hierarchical configuration merging
    
    Good first issue: Add support for YAML configuration files
    """
    
    def __init__(self):
        # Default configuration
        self._config = {
            "queue": {
                "concurrency_limits": {
                    "high": 10,
                    "medium": 5,
                    "low": 2
                },
                "queue_limits": {
                    "high": 50,
                    "medium": 100,
                    "low": 200
                }
            },
            "caching": {
                "default_ttl": 300,  # 5 minutes
                "enable_fallback": True,
                "max_stale_on_error": 3600,  # 1 hour
                "aggressive_fallback": {
                    "enabled": False,
                    "max_stale_duration": "24h"
                }
            },
            "storage": {
                "backend": "memory",
                "sqlite": {
                    "path": "data.db"
                }
            }
        }
        
        # Load configuration from file if exists
        self._load_config_file()
    
    def _load_config_file(self):
        """Load configuration from config.toml file"""
        config_path = Path("config.toml")
        if config_path.exists():
            try:
                with open(config_path, "rb") as f:
                    file_config = tomli.load(f)
                self._merge_config(file_config)
            except Exception as e:
                print(f"Warning: Could not load config.toml: {e}")
    
    def _merge_config(self, new_config: Dict[str, Any]):
        """Merge new configuration with existing configuration"""
        def merge_dict(base: Dict, update: Dict):
            for key, value in update.items():
                if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                    merge_dict(base[key], value)
                else:
                    base[key] = value
        
        merge_dict(self._config, new_config)
    
    def get(self, key_path: str, default=None):
        """
        Get configuration value by dot-separated key path.
        
        Args:
            key_path: Dot-separated path to configuration value (e.g., "queue.concurrency_limits.high")
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key_path.split(".")
        value = self._config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key_path: str, value):
        """
        Set configuration value by dot-separated key path.
        
        Args:
            key_path: Dot-separated path to configuration value
            value: Value to set
        """
        keys = key_path.split(".")
        config = self._config
        
        # Navigate to the parent of the target key
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        # Set the final value
        config[keys[-1]] = value


# Global configuration manager instance
_config_manager = ConfigManager()


def get_config(key_path: str, default=None):
    """
    Get configuration value by key path.
    
    Args:
        key_path: Dot-separated path to configuration value
        default: Default value if key not found
        
    Returns:
        Configuration value or default
    """
    return _config_manager.get(key_path, default)


def set_config(key_path: str, value):
    """
    Set configuration value by key path.
    
    Args:
        key_path: Dot-separated path to configuration value
        value: Value to set
    """
    _config_manager.set(key_path, value)


# Export public API
__all__ = ["get_config", "set_config", "ConfigManager"]