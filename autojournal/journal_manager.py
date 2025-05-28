"""Journal management and current task tracking"""

import os
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from .models import Task, ActivityAnalysis, JournalEntry, TaskStatus


class JournalManager:
    """Manages daily journals and current task display"""
    
    def __init__(self):
        self.current_task_file = Path.home() / ".current-task"
        self.journal_entries: List[JournalEntry] = []
        self.current_task: Optional[Task] = None
        self.session_start = datetime.now()
    
    def get_journal_path(self, date: datetime = None) -> Path:
        """Get the journal file path for a given date"""
        if date is None:
            date = datetime.now()
        
        filename = f"journal-{date.strftime('%Y-%m-%d')}.md"
        return Path.cwd() / filename
    
    def set_current_task(self, task: Task):
        """Set the current task and update the display file"""
        self.current_task = task
        self._update_current_task_display()
    
    def _update_current_task_display(self):
        """Update the ~/.current-task file for external display"""
        try:
            debug_file = Path.home() / ".autojournal-debug.log"
            with open(debug_file, "a") as f:
                from datetime import datetime
                timestamp = datetime.now().strftime("%H:%M:%S")
                
                if not self.current_task:
                    f.write(f"{timestamp}: _update_current_task_display called but no current task\n")
                    return
                
                content = f"Current: {self.current_task.description} | {self.current_task.progress_percentage}% | {self.current_task.estimated_time_minutes}min | {self.current_task.status.value}"
                f.write(f"{timestamp}: Writing to {self.current_task_file}: {content}\n")
                
                self.current_task_file.write_text(content)
                f.write(f"{timestamp}: Successfully wrote current task file\n")
                
        except Exception as e:
            debug_file = Path.home() / ".autojournal-debug.log"
            with open(debug_file, "a") as f:
                from datetime import datetime
                timestamp = datetime.now().strftime("%H:%M:%S")
                f.write(f"{timestamp}: Error updating current task display: {e}\n")
            print(f"Error updating current task display: {e}")
    
    async def log_task_start(self, task: Task):
        """Log the start of a new task"""
        entry = JournalEntry(
            timestamp=datetime.now(),
            entry_type="task_start",
            content=f"🎯 Started task: {task.description} (estimated {task.estimated_time_minutes} min)",
            task_context=task
        )
        
        self.journal_entries.append(entry)
        self._write_to_journal(entry)
        task.status = TaskStatus.IN_PROGRESS
        self._update_current_task_display()
    
    async def log_activity(self, analysis: ActivityAnalysis):
        """Log activity analysis to journal"""
        status_emoji = "✅" if analysis.is_on_task else "⚠️"
        confidence_text = f"({int(analysis.confidence * 100)}% confidence)"
        
        content = f"{status_emoji} {analysis.description} | App: {analysis.current_app} | Progress: {analysis.progress_estimate}% {confidence_text}"
        
        entry = JournalEntry(
            timestamp=analysis.timestamp,
            entry_type="activity",
            content=content,
            task_context=self.current_task
        )
        
        self.journal_entries.append(entry)
        self._write_to_journal(entry)
        
        # Update task progress if on-task
        if analysis.is_on_task and self.current_task:
            self.current_task.progress_percentage = max(
                self.current_task.progress_percentage,
                analysis.progress_estimate
            )
            self._update_current_task_display()
    
    async def log_task_completion(self, task: Task):
        """Log task completion"""
        entry = JournalEntry(
            timestamp=datetime.now(),
            entry_type="task_complete",
            content=f"✅ Completed task: {task.description}",
            task_context=task
        )
        
        self.journal_entries.append(entry)
        self._write_to_journal(entry)
        task.status = TaskStatus.COMPLETED
        task.progress_percentage = 100
        self._update_current_task_display()
    
    async def log_task_clarification(self, old_description: str, new_description: str):
        """Log task clarification/rewrite"""
        entry = JournalEntry(
            timestamp=datetime.now(),
            entry_type="task_clarify",
            content=f"📝 Task clarified: '{old_description}' → '{new_description}'",
            task_context=self.current_task
        )
        
        self.journal_entries.append(entry)
        self._write_to_journal(entry)
        self._update_current_task_display()
    
    async def log_task_hold(self, task: Task, reason: str):
        """Log putting task on hold"""
        entry = JournalEntry(
            timestamp=datetime.now(),
            entry_type="task_hold",
            content=f"⏸️ Put task on hold: {reason}",
            task_context=task
        )
        
        self.journal_entries.append(entry)
        self._write_to_journal(entry)
        task.status = TaskStatus.ON_HOLD
        self._update_current_task_display()
    
    async def log_task_resume(self, task: Task):
        """Log resuming task from hold"""
        entry = JournalEntry(
            timestamp=datetime.now(),
            entry_type="task_resume",
            content=f"▶️ Resumed task: {task.description}",
            task_context=task
        )
        
        self.journal_entries.append(entry)
        self._write_to_journal(entry)
        task.status = TaskStatus.IN_PROGRESS
        self._update_current_task_display()
    
    async def log_session_end(self):
        """Log end of session"""
        duration = datetime.now() - self.session_start
        entry = JournalEntry(
            timestamp=datetime.now(),
            entry_type="session_end",
            content=f"🏁 Session ended after {duration}",
            task_context=self.current_task
        )
        
        self.journal_entries.append(entry)
        self._write_to_journal(entry)
        
        # Clear current task display
        try:
            self.current_task_file.write_text("")
        except Exception as e:
            print(f"Error clearing current task display: {e}")
    
    def _write_to_journal(self, entry: JournalEntry):
        """Write entry to the daily journal file"""
        journal_path = self.get_journal_path(entry.timestamp)
        
        try:
            # Create journal file if it doesn't exist
            if not journal_path.exists():
                self._create_journal_file(journal_path)
            
            # Append entry to journal
            with open(journal_path, 'a', encoding='utf-8') as f:
                timestamp_str = entry.timestamp.strftime('%H:%M:%S')
                f.write(f"\n## {timestamp_str}\n")
                f.write(f"{entry.content}\n")
                
        except Exception as e:
            print(f"Error writing to journal: {e}")
    
    def _create_journal_file(self, journal_path: Path):
        """Create a new journal file with header"""
        date_str = datetime.now().strftime('%Y-%m-%d')
        header = f"""# Daily Journal - {date_str}

## Session Start - {datetime.now().strftime('%H:%M:%S')}
🚀 AutoJournal session started
"""
        
        journal_path.write_text(header, encoding='utf-8')
    
    def get_recent_entries(self, count: int = 5) -> List[JournalEntry]:
        """Get the most recent journal entries"""
        return self.journal_entries[-count:] if self.journal_entries else []
    
    def get_all_entries(self) -> List[JournalEntry]:
        """Get all journal entries from current session"""
        return self.journal_entries.copy()
    
    def get_current_task(self) -> Optional[Task]:
        """Get the current active task"""
        return self.current_task