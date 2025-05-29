"""Configuration management for AutoJournal AI models and settings"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
import json

class AutoJournalConfig:
    """Centralized configuration for AutoJournal AI models and settings"""
    
    # Default model configurations
    DEFAULT_MODELS = {
        "activity_analysis": "gpt-4o-mini",              # For screenshot analysis (vision capable)
        "goal_breakdown": "gpt-4o-mini",                 # For breaking goals into tasks
        "session_summary": "claude-3.5-sonnet-latest",  # For generating session summaries
        "fallback": "gpt-3.5-turbo"                     # Fallback model for any failures
    }
    
    # Default settings
    DEFAULT_SETTINGS = {
        "screenshot_interval": 10,          # seconds
        "max_screenshot_retries": 3,        # number of retries for screenshot capture
        "analysis_timeout": 30,             # seconds for AI analysis timeout
        "confidence_threshold": 0.3,        # minimum confidence for AI decisions
        "debug_logging": False              # enable debug logging
    }
    
    def __init__(self):
        self.config_dir = Path.home() / ".autojournal"
        self.config_file = self.config_dir / "config.json"
        self.config_dir.mkdir(exist_ok=True)
        
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default config"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                
                # Merge with defaults to ensure all keys exist
                merged_config = {
                    "models": {**self.DEFAULT_MODELS, **config.get("models", {})},
                    "settings": {**self.DEFAULT_SETTINGS, **config.get("settings", {})}
                }
                return merged_config
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error loading config: {e}. Using defaults.")
        
        # Return default configuration
        return {
            "models": self.DEFAULT_MODELS.copy(),
            "settings": self.DEFAULT_SETTINGS.copy()
        }
    
    def save_config(self) -> None:
        """Save current configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self._config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def get_model(self, purpose: str) -> str:
        """Get model name for a specific purpose"""
        return self._config["models"].get(purpose, self.DEFAULT_MODELS.get(purpose, "gpt-3.5-turbo"))
    
    def set_model(self, purpose: str, model_name: str) -> None:
        """Set model for a specific purpose"""
        self._config["models"][purpose] = model_name
        self.save_config()
    
    def get_setting(self, key: str) -> Any:
        """Get a setting value"""
        return self._config["settings"].get(key, self.DEFAULT_SETTINGS.get(key))
    
    def set_setting(self, key: str, value: Any) -> None:
        """Set a setting value"""
        self._config["settings"][key] = value
        self.save_config()
    
    def get_all_models(self) -> Dict[str, str]:
        """Get all configured models"""
        return self._config["models"].copy()
    
    def get_all_settings(self) -> Dict[str, Any]:
        """Get all configured settings"""
        return self._config["settings"].copy()
    
    def reset_to_defaults(self) -> None:
        """Reset configuration to defaults"""
        self._config = {
            "models": self.DEFAULT_MODELS.copy(),
            "settings": self.DEFAULT_SETTINGS.copy()
        }
        self.save_config()
    
    def print_config(self) -> None:
        """Print current configuration"""
        print("=== AutoJournal Configuration ===")
        print("\nAI Models:")
        for purpose, model in self._config["models"].items():
            print(f"  {purpose}: {model}")
        
        print("\nSettings:")
        for key, value in self._config["settings"].items():
            print(f"  {key}: {value}")
        
        print(f"\nConfig file: {self.config_file}")


# Global configuration instance
config = AutoJournalConfig()


def get_model(purpose: str) -> str:
    """Convenience function to get model for a purpose"""
    return config.get_model(purpose)


def get_setting(key: str) -> Any:
    """Convenience function to get a setting"""
    return config.get_setting(key)