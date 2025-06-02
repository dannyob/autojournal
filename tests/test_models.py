"""Tests for data models"""

from datetime import datetime
from autojournal.models import Task, Goal, ActivityAnalysis, JournalEntry, TaskStatus


class TestTask:
    def test_task_creation(self):
        task = Task(
            description="Write unit tests",
            estimated_time_minutes=30
        )
        
        assert task.description == "Write unit tests"
        assert task.estimated_time_minutes == 30
        assert task.status == TaskStatus.PENDING
        assert task.progress_percentage == 0
        assert task.created_at is not None
    
    def test_task_with_custom_values(self):
        custom_time = datetime(2023, 1, 1, 12, 0, 0)
        task = Task(
            description="Custom task",
            estimated_time_minutes=45,
            status=TaskStatus.IN_PROGRESS,
            progress_percentage=50,
            created_at=custom_time
        )
        
        assert task.status == TaskStatus.IN_PROGRESS
        assert task.progress_percentage == 50
        assert task.created_at == custom_time


class TestGoal:
    def test_goal_creation(self):
        goal = Goal(
            title="Complete project",
            description="Finish the AutoJournal project"
        )
        
        assert goal.title == "Complete project"
        assert goal.description == "Finish the AutoJournal project"
        assert goal.sub_tasks == []
    
    def test_goal_with_subtasks(self):
        task1 = Task("Task 1", 30)
        task2 = Task("Task 2", 45)
        
        goal = Goal(
            title="Complex goal",
            description="A goal with subtasks",
            sub_tasks=[task1, task2]
        )
        
        assert len(goal.sub_tasks) == 2
        assert goal.sub_tasks[0].description == "Task 1"
        assert goal.sub_tasks[1].description == "Task 2"


class TestActivityAnalysis:
    def test_activity_analysis_creation(self):
        analysis = ActivityAnalysis(
            timestamp=None,  # Should auto-set
            description="Working on code",
            current_app="VSCode",
            is_on_task=True,
            progress_estimate=75,
            confidence=0.9
        )
        
        assert analysis.description == "Working on code"
        assert analysis.current_app == "VSCode"
        assert analysis.is_on_task is True
        assert analysis.progress_estimate == 75
        assert analysis.confidence == 0.9
        assert analysis.timestamp is not None


class TestJournalEntry:
    def test_journal_entry_creation(self):
        task = Task("Test task", 30)
        entry = JournalEntry(
            timestamp=None,  # Should auto-set
            entry_type="task_start",
            content="Started working on task",
            task_context=task
        )
        
        assert entry.entry_type == "task_start"
        assert entry.content == "Started working on task"
        assert entry.task_context == task
        assert entry.timestamp is not None