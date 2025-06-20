"""Journal management and current task tracking"""

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
        self.is_on_task = True  # Track current on-task status
    
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
                
                # Add off-task indicator if currently off-task
                off_task_indicator = " ⚠️" if not self.is_on_task else ""
                content = f"Current: {self.current_task.description}{off_task_indicator} | {self.current_task.progress_percentage}% | {self.current_task.estimated_time_minutes}min | {self.current_task.status.value}"
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
        # Reset to on-task when starting a new task
        self.is_on_task = True
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
        
        # Update on-task status and refresh display if status changed
        old_status = self.is_on_task
        self.is_on_task = analysis.is_on_task
        
        # Update task progress if on-task
        if analysis.is_on_task and self.current_task:
            self.current_task.progress_percentage = max(
                self.current_task.progress_percentage,
                analysis.progress_estimate
            )
        
        # Update display if status changed or progress updated
        if old_status != self.is_on_task or analysis.is_on_task:
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
        # Reset to on-task when resuming a task
        self.is_on_task = True
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


class OrgmodeExporter:
    """Exports journal entries to orgmode worklog format using LLM"""
    
    def __init__(self, goals_file: str = "goals.md"):
        self.goals_file = Path(goals_file)
        self.onebig_file = Path("/users/danny/private/nextcloud/org/wiki/onebig.org")
    
    def export_journal_to_orgmode(self, target_date: datetime) -> str:
        """Export journal for a specific date to orgmode format"""
        journal_path = Path.cwd() / f"journal-{target_date.strftime('%Y-%m-%d')}.md"
        
        if not journal_path.exists():
            raise FileNotFoundError(f"Journal file not found: {journal_path}")
        
        return self.export_journal_file_to_orgmode(str(journal_path), target_date)
    
    def export_journal_file_to_orgmode(self, journal_file: str, target_date: datetime) -> str:
        """Export a specific journal file to orgmode format using LLM"""
        journal_path = Path(journal_file)
        
        if not journal_path.exists():
            raise FileNotFoundError(f"Journal file not found: {journal_path}")
        
        # Import llm library and config
        try:
            import llm
            from .config import config
        except ImportError:
            raise ImportError("llm library not installed. Run: pip install llm")
        
        # Read the necessary files
        try:
            with open(self.goals_file, 'r', encoding='utf-8') as f:
                goals_content = f.read()
        except Exception as e:
            goals_content = f"Error reading goals file: {e}"
        
        try:
            with open(self.onebig_file, 'r', encoding='utf-8') as f:
                onebig_content = f.read()
        except Exception as e:
            onebig_content = f"Error reading onebig file: {e}"
        
        with open(journal_path, 'r', encoding='utf-8') as f:
            journal_content = f.read()
        
        # Get the prompt template from config
        prompt_template = config.get_prompt("orgmode_export")
        
        # Format the prompt with actual content
        prompt = prompt_template.format(
            date=target_date.strftime('%Y-%m-%d %a'),
            goals_content=goals_content,
            onebig_content=onebig_content,
            journal_date=target_date.strftime('%Y-%m-%d'),
            journal_content=journal_content
        )
        
        # Get the model from config
        model_name = config.get_model("orgmode_export")
        
        try:
            model = llm.get_model(model_name)
        except Exception as e:
            # Try fallback model
            fallback_model = config.get_model("fallback")
            print(f"Warning: Could not load model '{model_name}': {e}")
            print(f"Using fallback model: {fallback_model}")
            model = llm.get_model(fallback_model)
        
        # Run the prompt through the LLM
        response = model.prompt(prompt)
        
        return self._extract_code_blocks(response.text())
    
    def _extract_code_blocks(self, text: str) -> str:
        """Extract content between first markdown code fence (like llm -x option)"""
        import re
        
        # Pattern to match markdown code blocks: ```language\ncontent\n```
        pattern = r'```(?:[a-zA-Z0-9_+-]*\n)?(.*?)```'
        match = re.search(pattern, text, re.DOTALL)
        
        if match:
            return match.group(1).strip()
        else:
            # If no code blocks found, return the full response
            return text