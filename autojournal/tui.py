"""Terminal User Interface for AutoJournal"""

import asyncio
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static, Button, Input, TextArea
from textual.binding import Binding
from textual.screen import ModalScreen
from textual import events

from .models import Task


class TaskClarificationModal(ModalScreen):
    """Modal for clarifying/editing task description"""
    
    def __init__(self, current_description: str):
        super().__init__()
        self.current_description = current_description
        self.new_description = current_description
    
    def compose(self) -> ComposeResult:
        yield Container(
            Static("Clarify Task Description:", classes="modal-title"),
            Input(
                value=self.current_description,
                placeholder="Enter new task description...",
                id="task-input"
            ),
            Horizontal(
                Button("Save", variant="primary", id="save"),
                Button("Cancel", id="cancel"),
                classes="modal-buttons"
            ),
            classes="modal"
        )
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            input_widget = self.query_one("#task-input", Input)
            self.new_description = input_widget.value
            self.dismiss(self.new_description)
        elif event.button.id == "cancel":
            self.dismiss(None)


class AutoJournalTUI(App):
    """Main TUI application for AutoJournal"""
    
    TITLE = "AutoJournal - Productivity Tracker"
    
    BINDINGS = [
        Binding("c", "mark_complete", "Complete Task"),
        Binding("e", "clarify_task", "Edit Task"),
        Binding("h", "hold_task", "Hold Task"),
        Binding("r", "resume_task", "Resume Task"),
        Binding("q", "quit_app", "Quit"),
    ]
    
    CSS = """
    .task-info {
        background: $surface;
        border: solid $accent;
        margin: 1;
        padding: 1;
    }
    
    .status-panel {
        background: $surface;
        border: solid $accent;
        margin: 1;
        padding: 1;
        height: 8;
    }
    
    .controls {
        background: $surface;
        border: solid $accent;
        margin: 1;
        padding: 1;
        height: 12;
    }
    
    .modal {
        align: center middle;
        background: $surface;
        border: solid $accent;
        width: 60;
        height: 10;
        padding: 1;
    }
    
    .modal-title {
        text-align: center;
        margin-bottom: 1;
    }
    
    .modal-buttons {
        align: center middle;
        margin-top: 1;
    }
    
    Button {
        margin: 0 1;
    }
    """
    
    def __init__(self, autojournal_app):
        super().__init__()
        self.autojournal_app = autojournal_app
        self.current_task = None
        self.on_task = True
        self.last_activity = "Starting session..."
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        with Vertical():
            with Container(classes="task-info"):
                yield Static("Current Task:", id="task-label")
                yield Static("No task loaded", id="current-task")
                yield Static("Progress: 0%", id="progress")
            
            with Container(classes="status-panel"):
                yield Static("Status:", id="status-label")
                yield Static("✅ On Task", id="status")
                yield Static("Last Activity:", id="activity-label")
                yield Static("Starting session...", id="last-activity")
            
            with Container(classes="controls"):
                yield Static("Controls:", id="controls-label")
                yield Button("✅ Complete Task (c)", id="complete", variant="success")
                yield Button("📝 Edit Task (e)", id="edit", variant="primary")
                yield Button("⏸️ Hold Task (h)", id="hold", variant="warning")
                yield Button("▶️ Resume Task (r)", id="resume")
                yield Button("🏁 End Session (q)", id="quit", variant="error")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Set up the TUI when it starts"""
        self.set_interval(1.0, self.update_display)
        # Start monitoring loop in background
        self.set_interval(10.0, self.take_screenshot_and_analyze)
    
    def update_display(self) -> None:
        """Update the display with current information"""
        # Get current task info
        if self.autojournal_app.current_task:
            task = self.autojournal_app.current_task
            self.query_one("#current-task", Static).update(
                f"{task.description} ({task.estimated_time_minutes} min)"
            )
            self.query_one("#progress", Static).update(
                f"Progress: {task.progress_percentage}% | Status: {task.status.value}"
            )
        
        # Update activity status
        recent_entries = self.autojournal_app.journal_manager.get_recent_entries(1)
        if recent_entries:
            latest = recent_entries[0]
            status_text = "✅ On Task" if "✅" in latest.content else "⚠️ Off Task"
            self.query_one("#status", Static).update(status_text)
            
            # Clean up the activity description
            activity_desc = latest.content.split(" | ")[0].replace("✅ ", "").replace("⚠️ ", "")
            self.query_one("#last-activity", Static).update(activity_desc)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if event.button.id == "complete":
            self.action_mark_complete()
        elif event.button.id == "edit":
            self.action_clarify_task()
        elif event.button.id == "hold":
            self.action_hold_task()
        elif event.button.id == "resume":
            self.action_resume_task()
        elif event.button.id == "quit":
            self.action_quit_app()
    
    def action_mark_complete(self) -> None:
        """Mark current task as complete"""
        if self.autojournal_app.current_task:
            asyncio.create_task(self.autojournal_app.mark_task_complete())
            self.notify("Task marked as complete! 🎉")
    
    def action_clarify_task(self) -> None:
        """Open modal to clarify task description"""
        if self.autojournal_app.current_task:
            current_desc = self.autojournal_app.current_task.description
            
            def handle_clarification(new_description):
                if new_description and new_description != current_desc:
                    asyncio.create_task(
                        self.autojournal_app.clarify_task(new_description)
                    )
                    self.notify("Task description updated! 📝")
            
            self.push_screen(
                TaskClarificationModal(current_desc),
                handle_clarification
            )
    
    def action_hold_task(self) -> None:
        """Put current task on hold"""
        if self.autojournal_app.current_task:
            asyncio.create_task(
                self.autojournal_app.put_task_on_hold("User requested hold")
            )
            self.notify("Task put on hold ⏸️")
    
    def action_resume_task(self) -> None:
        """Resume current task from hold"""
        if self.autojournal_app.current_task:
            asyncio.create_task(self.autojournal_app.resume_task())
            self.notify("Task resumed! ▶️")
    
    def action_quit_app(self) -> None:
        """End session and quit application"""
        asyncio.create_task(self.autojournal_app.end_session())
        self.exit()
    
    def take_screenshot_and_analyze(self) -> None:
        """Take screenshot and analyze activity (called by timer)"""
        try:
            # Run the async analysis in a new event loop
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            analysis = loop.run_until_complete(
                self.autojournal_app.screenshot_analyzer.analyze_current_activity(
                    self.autojournal_app.current_task,
                    self.autojournal_app.journal_manager.get_recent_entries()
                )
            )
            
            # Log the analysis
            loop.run_until_complete(
                self.autojournal_app.journal_manager.log_activity(analysis)
            )
            
            loop.close()
            
        except Exception as e:
            # Don't crash the TUI if analysis fails
            print(f"Analysis error: {e}")
    
    def run_app(self):
        """Run the TUI application"""
        return self.run()