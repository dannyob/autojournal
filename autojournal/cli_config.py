#!/usr/bin/env python3
"""Command-line configuration tool for AutoJournal"""

import argparse
import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import config


def list_models():
    """List all available models"""
    print("Available models:")
    try:
        import llm
        models = llm.get_models()
        for model in models:
            print(f"  {model.model_id}")
    except ImportError:
        print("  llm library not installed")
    except Exception as e:
        print(f"  Error listing models: {e}")


def show_config():
    """Show current configuration"""
    config.print_config()


def set_model_config(purpose: str, model_name: str):
    """Set model for a specific purpose"""
    valid_purposes = ["activity_analysis", "goal_breakdown", "session_summary", "fallback"]
    
    if purpose not in valid_purposes:
        print(f"Error: Invalid purpose '{purpose}'")
        print(f"Valid purposes: {', '.join(valid_purposes)}")
        return False
    
    config.set_model(purpose, model_name)
    print(f"Set {purpose} model to: {model_name}")
    return True


def set_setting_config(key: str, value: str):
    """Set a configuration setting"""
    valid_settings = ["screenshot_interval", "max_screenshot_retries", "analysis_timeout", 
                     "confidence_threshold", "debug_logging"]
    
    if key not in valid_settings:
        print(f"Error: Invalid setting '{key}'")
        print(f"Valid settings: {', '.join(valid_settings)}")
        return False
    
    # Convert value to appropriate type
    try:
        if key in ["screenshot_interval", "max_screenshot_retries", "analysis_timeout"]:
            value = int(value)
        elif key == "confidence_threshold":
            value = float(value)
        elif key == "debug_logging":
            value = value.lower() in ["true", "1", "yes", "on"]
    except ValueError:
        print(f"Error: Invalid value '{value}' for setting '{key}'")
        return False
    
    config.set_setting(key, value)
    print(f"Set {key} to: {value}")
    return True


def reset_config():
    """Reset configuration to defaults"""
    response = input("Are you sure you want to reset all configuration to defaults? (y/N): ")
    if response.lower() in ['y', 'yes']:
        config.reset_to_defaults()
        print("Configuration reset to defaults")
    else:
        print("Reset cancelled")


def main():
    parser = argparse.ArgumentParser(description="AutoJournal Configuration Tool")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Show configuration
    subparsers.add_parser('show', help='Show current configuration')
    
    # List available models
    subparsers.add_parser('list-models', help='List available AI models')
    
    # Set model
    model_parser = subparsers.add_parser('set-model', help='Set AI model for a purpose')
    model_parser.add_argument('purpose', help='Purpose: activity_analysis, goal_breakdown, session_summary, fallback')
    model_parser.add_argument('model', help='Model name (e.g., claude-3.5-sonnet-latest)')
    
    # Set setting
    setting_parser = subparsers.add_parser('set-setting', help='Set a configuration setting')
    setting_parser.add_argument('key', help='Setting key')
    setting_parser.add_argument('value', help='Setting value')
    
    # Reset configuration
    subparsers.add_parser('reset', help='Reset configuration to defaults')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == 'show':
        show_config()
    elif args.command == 'list-models':
        list_models()
    elif args.command == 'set-model':
        set_model_config(args.purpose, args.model)
    elif args.command == 'set-setting':
        set_setting_config(args.key, args.value)
    elif args.command == 'reset':
        reset_config()


if __name__ == "__main__":
    main()