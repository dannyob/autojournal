"""AutoJournal - Intelligent productivity tracking system"""

from .goal_manager import GoalManager
from .journal_manager import JournalManager
from .screenshot_analyzer import ScreenshotAnalyzer
from .models import Task, Goal, ActivityAnalysis

__version__ = "0.1.0"
__all__ = ["GoalManager", "JournalManager", "ScreenshotAnalyzer", "Task", "Goal", "ActivityAnalysis"]