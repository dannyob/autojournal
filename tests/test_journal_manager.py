"""Tests for JournalManager"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime
from autojournal.journal_manager import JournalManager
from autojournal.models import Task, ActivityAnalysis, TaskStatus


class TestJournalManager:
    def setup_method(self):
        self.journal_manager = JournalManager()
        # Use a temporary file for current task display
        self.temp_file = tempfile.NamedTemporaryFile(delete=False)
        self.journal_manager.current_task_file = Path(self.temp_file.name)
    
    def teardown_method(self):
        # Clean up temp file
        if self.journal_manager.current_task_file.exists():
            self.journal_manager.current_task_file.unlink()
    
    def test_get_journal_path(self):
        test_date = datetime(2023, 12, 25, 14, 30, 0)
        path = self.journal_manager.get_journal_path(test_date)
        
        assert path.name == "journal-2023-12-25.md"
        assert path.parent == Path.cwd()
    
    def test_get_journal_path_default_date(self):
        path = self.journal_manager.get_journal_path()
        today = datetime.now().strftime('%Y-%m-%d')
        
        assert path.name == f"journal-{today}.md"
    
    def test_set_current_task(self):
        task = Task("Test task", 30)
        self.journal_manager.set_current_task(task)
        
        assert self.journal_manager.current_task == task
        
        # Check that current task file was updated
        assert self.journal_manager.current_task_file.exists()
        content = self.journal_manager.current_task_file.read_text()
        assert "Test task" in content
        assert "30 minutes" in content
    
    @pytest.mark.asyncio
    async def test_log_task_start(self):
        task = Task("Test task", 30)
        await self.journal_manager.log_task_start(task)
        
        assert task.status == TaskStatus.IN_PROGRESS
        assert len(self.journal_manager.journal_entries) == 1
        
        entry = self.journal_manager.journal_entries[0]
        assert entry.entry_type == "task_start"
        assert "Test task" in entry.content
        assert entry.task_context == task
    
    @pytest.mark.asyncio
    async def test_log_activity(self):
        task = Task("Current task", 30)
        self.journal_manager.set_current_task(task)
        
        analysis = ActivityAnalysis(
            timestamp=datetime.now(),
            description="Working on code",
            current_app="VSCode",
            is_on_task=True,
            progress_estimate=50,
            confidence=0.8
        )
        
        await self.journal_manager.log_activity(analysis)
        
        assert len(self.journal_manager.journal_entries) == 1
        entry = self.journal_manager.journal_entries[0]
        assert entry.entry_type == "activity"
        assert "Working on code" in entry.content
        assert "VSCode" in entry.content
        assert "50%" in entry.content
        assert task.progress_percentage == 50  # Should be updated
    
    @pytest.mark.asyncio
    async def test_log_activity_off_task(self):
        analysis = ActivityAnalysis(
            timestamp=datetime.now(),
            description="Browsing social media",
            current_app="Facebook",
            is_on_task=False,
            progress_estimate=0,
            confidence=0.9
        )
        
        await self.journal_manager.log_activity(analysis)
        
        entry = self.journal_manager.journal_entries[0]
        assert "⚠️" in entry.content
        assert "Browsing social media" in entry.content
    
    @pytest.mark.asyncio
    async def test_log_task_completion(self):
        task = Task("Test task", 30)
        await self.journal_manager.log_task_completion(task)
        
        assert task.status == TaskStatus.COMPLETED
        assert task.progress_percentage == 100
        
        entry = self.journal_manager.journal_entries[0]
        assert entry.entry_type == "task_complete"
        assert "Completed task" in entry.content
    
    @pytest.mark.asyncio
    async def test_log_task_clarification(self):
        task = Task("Original task", 30)
        self.journal_manager.set_current_task(task)
        
        await self.journal_manager.log_task_clarification(
            "Original task", 
            "Updated task description"
        )
        
        entry = self.journal_manager.journal_entries[0]
        assert entry.entry_type == "task_clarify"
        assert "Original task" in entry.content
        assert "Updated task description" in entry.content
    
    def test_get_recent_entries(self):
        # Add some test entries
        self.journal_manager.journal_entries = [
            self.journal_manager.journal_entries[i] if i < len(self.journal_manager.journal_entries) 
            else type('MockEntry', (), {
                'timestamp': datetime.now(),
                'entry_type': 'test',
                'content': f'Entry {i}',
                'task_context': None
            })() for i in range(7)
        ]
        
        # Manually create mock entries since we don't have real ones
        from autojournal.models import JournalEntry
        for i in range(7):
            entry = JournalEntry(
                timestamp=datetime.now(),
                entry_type='test',
                content=f'Entry {i}',
                task_context=None
            )
            self.journal_manager.journal_entries.append(entry)
        
        recent = self.journal_manager.get_recent_entries(3)
        assert len(recent) == 3
        assert recent[-1].content == 'Entry 6'  # Most recent
    
    def test_get_current_task(self):
        task = Task("Current task", 30)
        self.journal_manager.set_current_task(task)
        
        assert self.journal_manager.get_current_task() == task
    
    def test_get_current_task_none(self):
        assert self.journal_manager.get_current_task() is None