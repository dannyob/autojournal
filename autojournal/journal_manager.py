"""Journal management and current task tracking"""

from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Tuple
import re

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
    """Exports journal entries to orgmode worklog format"""
    
    def __init__(self, goals_file: str = "goals.md"):
        self.goals_file = Path(goals_file)
    
    def export_journal_to_orgmode(self, target_date: datetime) -> str:
        """Export journal for a specific date to orgmode format"""
        journal_path = Path.cwd() / f"journal-{target_date.strftime('%Y-%m-%d')}.md"
        
        if not journal_path.exists():
            raise FileNotFoundError(f"Journal file not found: {journal_path}")
        
        return self.export_journal_file_to_orgmode(str(journal_path), target_date)
    
    def export_journal_file_to_orgmode(self, journal_file: str, target_date: datetime) -> str:
        """Export a specific journal file to orgmode format"""
        journal_path = Path(journal_file)
        
        if not journal_path.exists():
            raise FileNotFoundError(f"Journal file not found: {journal_path}")
        
        # Parse journal entries
        entries = self._parse_journal_file(journal_path)
        
        # Group entries into work chunks and distractions
        work_chunks, distractions = self._analyze_work_patterns(entries)
        
        # Generate orgmode content
        return self._generate_orgmode_content(work_chunks, distractions, target_date)
    
    def _parse_journal_file(self, journal_path: Path) -> List[Dict]:
        """Parse journal file into structured entries"""
        entries = []
        
        with open(journal_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split by timestamp headers
        timestamp_pattern = r'## (\d{2}:\d{2}:\d{2})'
        sections = re.split(timestamp_pattern, content)
        
        # Skip the first section (header)
        for i in range(1, len(sections), 2):
            if i + 1 < len(sections):
                timestamp_str = sections[i]
                entry_content = sections[i + 1].strip()
                
                if entry_content:
                    # Parse timestamp
                    timestamp = datetime.strptime(timestamp_str, '%H:%M:%S').time()
                    
                    # Determine entry type and extract info
                    entry = self._parse_entry_content(timestamp, entry_content)
                    if entry:
                        entries.append(entry)
        
        return entries
    
    def _parse_entry_content(self, timestamp, content: str) -> Optional[Dict]:
        """Parse individual journal entry content"""
        entry = {
            'timestamp': timestamp,
            'content': content,
            'type': 'unknown',
            'is_on_task': None,
            'task_description': None,
            'app': None,
            'progress': None
        }
        
        # Identify entry type
        if '🎯 Started task:' in content:
            entry['type'] = 'task_start'
            match = re.search(r'Started task: (.+?) \(estimated', content)
            if match:
                entry['task_description'] = match.group(1)
        elif '✅ Completed task:' in content:
            entry['type'] = 'task_complete'
            match = re.search(r'Completed task: (.+)', content)
            if match:
                entry['task_description'] = match.group(1)
        elif '📝 Task clarified:' in content:
            entry['type'] = 'task_clarify'
        elif '⏸️ Put task on hold:' in content:
            entry['type'] = 'task_hold'
        elif '▶️ Resumed task:' in content:
            entry['type'] = 'task_resume'
        elif '🏁 Session ended' in content:
            entry['type'] = 'session_end'
        elif '✅' in content or '⚠️' in content:
            entry['type'] = 'activity'
            entry['is_on_task'] = '✅' in content
            
            # Extract app and progress
            app_match = re.search(r'App: ([^|]+)', content)
            if app_match:
                entry['app'] = app_match.group(1).strip()
            
            progress_match = re.search(r'Progress: (\d+)%', content)
            if progress_match:
                entry['progress'] = int(progress_match.group(1))
        
        return entry
    
    def _analyze_work_patterns(self, entries: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """Analyze entries to identify work chunks and distractions"""
        work_chunks = []
        distractions = []
        
        current_chunk = None
        current_task = None
        
        for entry in entries:
            if entry['type'] == 'task_start':
                # Start new work chunk
                if current_chunk:
                    work_chunks.append(current_chunk)
                
                current_task = entry['task_description']
                current_chunk = {
                    'task': current_task,
                    'start_time': entry['timestamp'],
                    'end_time': None,
                    'focused_periods': [],
                    'distraction_periods': []
                }
                
            elif entry['type'] in ['task_complete', 'task_hold', 'session_end']:
                # End current work chunk
                if current_chunk:
                    current_chunk['end_time'] = entry['timestamp']
                    work_chunks.append(current_chunk)
                    current_chunk = None
                
            elif entry['type'] == 'task_resume':
                # Resume work chunk
                if current_chunk:
                    current_chunk['end_time'] = None
                
            elif entry['type'] == 'activity' and current_chunk:
                # Add to current chunk
                period = {
                    'timestamp': entry['timestamp'],
                    'is_on_task': entry['is_on_task'],
                    'app': entry['app'],
                    'content': entry['content']
                }
                
                if entry['is_on_task']:
                    current_chunk['focused_periods'].append(period)
                else:
                    current_chunk['distraction_periods'].append(period)
                    distractions.append(period)
        
        # Close any remaining chunk
        if current_chunk:
            current_chunk['end_time'] = entries[-1]['timestamp'] if entries else current_chunk['start_time']
            work_chunks.append(current_chunk)
        
        return work_chunks, distractions
    
    def _generate_orgmode_content(self, work_chunks: List[Dict], distractions: List[Dict], target_date: datetime) -> str:
        """Generate orgmode worklog content"""
        content = []
        
        # Generate work chunks
        for chunk in work_chunks:
            if chunk['focused_periods']:
                # Calculate total focused time
                total_minutes = self._calculate_focused_time(chunk['focused_periods'])
                
                # Format task header with timestamp
                date_prefix = target_date.strftime("<%Y-%m-%d %a %H:%M>")
                task_title = f"* {date_prefix} {chunk['task']}"
                content.append(task_title)
                
                # Add CLOCK entry
                start_time = chunk['start_time'].strftime("%H:%M")
                end_time = chunk['end_time'].strftime("%H:%M") if chunk['end_time'] else start_time
                clock_entry = f"CLOCK: [{target_date.strftime('%Y-%m-%d %a')} {start_time}]--[{target_date.strftime('%Y-%m-%d %a')} {end_time}] =>  {total_minutes//60:02d}:{total_minutes%60:02d}"
                content.append(f"  {clock_entry}")
                
                # Add relevant tag
                content.append("  :PROPERTIES:")
                content.append("  :TAG: work")
                content.append("  :END:")
                content.append("")
        
        # Generate distractions summary
        if distractions:
            date_prefix = target_date.strftime("<%Y-%m-%d %a %H:%M>")
            content.append(f"* {date_prefix} Other tasks and distractions")
            
            # Group distractions by app/type
            distraction_summary = self._summarize_distractions(distractions)
            
            for app, periods in distraction_summary.items():
                total_minutes = len(periods) * 10 // 60  # Approximate based on 10-second intervals
                content.append(f"  - {app}: ~{total_minutes} minutes")
                for period in periods:
                    timestamp = period['timestamp'].strftime("%H:%M")
                    content.append(f"    - {timestamp}: {period['content']}")
            
            content.append("  :PROPERTIES:")
            content.append("  :TAG: distraction")
            content.append("  :END:")
        
        return "\n".join(content)
    
    def _calculate_focused_time(self, focused_periods: List[Dict]) -> int:
        """Calculate total focused time in minutes"""
        # Each period represents ~10 seconds of activity
        # This is a rough approximation
        return len(focused_periods) * 10 // 60
    
    def _summarize_distractions(self, distractions: List[Dict]) -> Dict[str, List[Dict]]:
        """Group distractions by app/type"""
        summary = {}
        
        for distraction in distractions:
            app = distraction.get('app', 'Unknown')
            if app not in summary:
                summary[app] = []
            summary[app].append(distraction)
        
        return summary