"""Configuration management for AutoJournal AI models and settings"""

from pathlib import Path
from typing import Dict, Any
import json

class AutoJournalConfig:
    """Centralized configuration for AutoJournal AI models and settings"""
    
    # Default model configurations
    DEFAULT_MODELS = {
        "activity_analysis": "gemini-1.5-flash-latest", # For screenshot analysis (vision capable, cost-effective)
        "goal_breakdown": "gpt-4o-mini",                # For breaking goals into tasks
        "session_summary": "claude-3.5-sonnet-latest", # For generating session summaries
        "orgmode_export": "gpt-4o-mini",               # For converting journal to orgmode worklog
        "fallback": "gpt-3.5-turbo"                    # Fallback model for any failures
    }
    
    # Default settings
    DEFAULT_SETTINGS = {
        "screenshot_interval": 10,          # seconds
        "max_screenshot_retries": 3,        # number of retries for screenshot capture
        "analysis_timeout": 30,             # seconds for AI analysis timeout
        "confidence_threshold": 0.3,        # minimum confidence for AI decisions
        "debug_logging": False              # enable debug logging
    }
    
    # Default prompts for different AI purposes
    DEFAULT_PROMPTS = {
        "activity_analysis_vision": """Analyze the screenshot to determine what the user is currently doing and whether they are working on their SPECIFIC assigned task.

{task_context}

Active application: {active_app}

{recent_context}

Look at the screenshot and provide analysis in JSON format:
{{
    "description": "Detailed description of what the user is doing based on the screen content",
    "is_on_task": true/false,
    "progress_estimate": 0-100,
    "confidence": 0.0-1.0
}}

CRITICAL: Only set is_on_task=true if the visible work directly contributes to the SPECIFIC task above.

Guidelines for is_on_task assessment:
✅ ON-TASK (true):
- Working on files, documents, or code directly related to the assigned task
- Research, planning, or tools that clearly support the current task
- Communication/emails specifically about the current task

❌ OFF-TASK (false):
- Working on different projects, even if productive work
- Social media, entertainment, news, or personal browsing
- Email/messaging unrelated to the current task
- Documentation or planning for other tasks/projects
- Even high-quality work that doesn't match the assigned task

If you see focused work on something other than the assigned task, flag it as OFF-TASK and mention "working on different task" in the description.

Base progress estimate on visible completion of the ASSIGNED task only.
Set confidence based on how clearly you can determine task alignment from the screenshot.""",
        
        "activity_analysis_text": """Analyze the current activity based on the active application and context to determine if they are working on their SPECIFIC assigned task.

{task_context}

Active application: {active_app}

{recent_context}

Based on the active application and context, provide analysis in JSON format:
{{
    "description": "Brief description of what the user appears to be doing",
    "is_on_task": true/false,
    "progress_estimate": 0-100,
    "confidence": 0.0-1.0
}}

CRITICAL: Only set is_on_task=true if the activity likely contributes to the SPECIFIC task above.

Guidelines for is_on_task assessment:
✅ ON-TASK (true):
- Using development tools (IDE, terminal) when task involves coding
- Using document editors when task involves writing/documentation  
- Using task-specific applications that match the assigned work

❌ OFF-TASK (false):
- Social media, entertainment, news applications
- Email/messaging unless specifically task-related
- Different development projects (even if productive work)
- Applications that don't align with the current task type

Note: This analysis is based only on application name and recent context since no screenshot is available.
Use recent context to determine if the current application use aligns with the assigned task pattern.
If recent entries show work on different tasks, be more skeptical about current activity.""",
        
        "goal_breakdown": """Break down the following goal into 3-5 actionable sub-tasks that can be completed in a work session.

Goal: {goal_title}
Description: {goal_description}

Return your response as a JSON array of task objects:
{{
    "tasks": [
        {{
            "title": "Clear, actionable task title",
            "description": "Specific description of what needs to be done",
            "estimated_minutes": 15-90
        }}
    ]
}}

Guidelines:
- Tasks should be specific and actionable (start with action verbs)
- Each task should take 15-90 minutes to complete
- Break large tasks into smaller, manageable pieces
- Consider dependencies and logical order
- Focus on concrete deliverables""",
        
        "session_summary": """Generate a productivity summary and insights for this work session.

{task_context}

{activity_summary}

Create a summary that includes:
1. Overview of time spent and main activities
2. Assessment of focus and productivity 
3. Tasks completed vs planned
4. Recommendations for improving focus and efficiency
5. Overall productivity rating (1-10)

Keep the summary concise but actionable.""",
        
        "orgmode_export": """Convert this journal into a orgmode worklog, based on the TODO categories in the listed onebig orgfile. Identify the actual intended goals, and record CLOCK entries based on successfully non-distracted chunks of time. Create another action, that records in its worklog all the other tasks/distractions that were performed. Make sure that the CLOCK entries for the intended goals and those of the task/distractions exclude each other. Provide timestamps (separate from the clock entries) that list the time spent on other task/directions in the other action. Include in the title of each action a prefix of a timestamp of the date started in the form <{date} HH:MM>. Add a relevant :TAG: to both action entries.

# Goals File (goals.md):
{goals_content}

# Onebig Org File:
{onebig_content}

# Journal for {journal_date}:
{journal_content}"""
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
                    "settings": {**self.DEFAULT_SETTINGS, **config.get("settings", {})},
                    "prompts": {**self.DEFAULT_PROMPTS, **config.get("prompts", {})}
                }
                return merged_config
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error loading config: {e}. Using defaults.")
        
        # Return default configuration and save it
        default_config = {
            "models": self.DEFAULT_MODELS.copy(),
            "settings": self.DEFAULT_SETTINGS.copy(),
            "prompts": self.DEFAULT_PROMPTS.copy()
        }
        
        # Save the default configuration to file
        try:
            with open(self.config_file, 'w') as f:
                json.dump(default_config, f, indent=2)
            print(f"Created default configuration at: {self.config_file}")
        except Exception as e:
            print(f"Warning: Could not save default config: {e}")
        
        return default_config
    
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
    
    def get_prompt(self, purpose: str) -> str:
        """Get prompt for a specific purpose"""
        return self._config["prompts"].get(purpose, self.DEFAULT_PROMPTS.get(purpose, ""))
    
    def set_prompt(self, purpose: str, prompt: str) -> None:
        """Set prompt for a specific purpose"""
        self._config["prompts"][purpose] = prompt
        self.save_config()
    
    def get_all_prompts(self) -> Dict[str, str]:
        """Get all configured prompts"""
        return self._config["prompts"].copy()
    
    def reset_to_defaults(self) -> None:
        """Reset configuration to defaults"""
        self._config = {
            "models": self.DEFAULT_MODELS.copy(),
            "settings": self.DEFAULT_SETTINGS.copy(),
            "prompts": self.DEFAULT_PROMPTS.copy()
        }
        self.save_config()
    
    def generate_default_config(self, force: bool = False) -> None:
        """Generate default configuration file"""
        if self.config_file.exists() and not force:
            print(f"Configuration file already exists: {self.config_file}")
            print("Use --force to overwrite existing configuration")
            return
        
        default_config = {
            "models": self.DEFAULT_MODELS.copy(),
            "settings": self.DEFAULT_SETTINGS.copy(),
            "prompts": self.DEFAULT_PROMPTS.copy()
        }
        
        try:
            self.config_dir.mkdir(exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(default_config, f, indent=2)
            print(f"Generated default configuration at: {self.config_file}")
            
            # Update internal config
            self._config = default_config
            
        except Exception as e:
            print(f"Error generating default config: {e}")
    
    def print_config(self) -> None:
        """Print current configuration"""
        print("=== AutoJournal Configuration ===")
        print("\nAI Models:")
        for purpose, model in self._config["models"].items():
            print(f"  {purpose}: {model}")
        
        print("\nSettings:")
        for key, value in self._config["settings"].items():
            print(f"  {key}: {value}")
        
        print("\nPrompts:")
        for purpose, prompt in self._config["prompts"].items():
            # Show first line of prompt only
            first_line = prompt.split('\n')[0][:60]
            if len(prompt) > 60:
                first_line += "..."
            print(f"  {purpose}: {first_line}")
        
        print(f"\nConfig file: {self.config_file}")


# Global configuration instance
config = AutoJournalConfig()


def get_model(purpose: str) -> str:
    """Convenience function to get model for a purpose"""
    return config.get_model(purpose)


def get_setting(key: str) -> Any:
    """Convenience function to get a setting"""
    return config.get_setting(key)


def get_prompt(purpose: str) -> str:
    """Convenience function to get a prompt"""
    return config.get_prompt(purpose)