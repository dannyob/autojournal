"""Data models for AutoJournal"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from enum import Enum


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"


@dataclass
class Task:
    """Represents a single task or sub-goal"""
    description: str
    estimated_time_minutes: int
    status: TaskStatus = TaskStatus.PENDING
    progress_percentage: int = 0
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class Goal:
    """Represents a high-level goal"""
    title: str
    description: str
    sub_tasks: List[Task] = None
    
    def __post_init__(self):
        if self.sub_tasks is None:
            self.sub_tasks = []


@dataclass
class ActivityAnalysis:
    """Analysis of current screen activity"""
    timestamp: datetime
    description: str
    current_app: str
    is_on_task: bool
    progress_estimate: int  # 0-100
    confidence: float  # 0.0-1.0
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class JournalEntry:
    """A single journal entry"""
    timestamp: datetime
    entry_type: str  # 'task_start', 'activity', 'task_complete', etc.
    content: str
    task_context: Optional[Task] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()