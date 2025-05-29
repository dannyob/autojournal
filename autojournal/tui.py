"""Terminal User Interface for AutoJournal"""

import asyncio
from pathlib import Path
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static, Button, Input, TextArea, OptionList
from textual.widgets.option_list import Option
from textual.binding import Binding
from textual.screen import ModalScreen
from textual import events

from .models import Task
from .config import get_setting
from .notifier import NotificationManager


class TaskClarificationModal(ModalScreen):
    """Modal for clarifying/editing task description"""
    
    def __init__(self, current_description: str):
        super().__init__()
        self.current_description = current_description
        self.new_description = current_description
    
    def _enable_mouse_support(self) -> bool:
        """Disable mouse support to prevent coordinate output"""
        return False
    
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


class TaskSelectionModal(ModalScreen):
    """Modal for selecting a task from available goals"""
    
    def __init__(self, available_tasks: list):
        super().__init__()
        self.available_tasks = available_tasks
        self.selected_task = None
    
    def _enable_mouse_support(self) -> bool:
        """Disable mouse support to prevent coordinate output"""
        return False
    
    def compose(self) -> ComposeResult:
        options = []
        for i, (goal_title, task) in enumerate(self.available_tasks):
            # Clean up task description to remove redundant goal title
            task_desc = task.description
            if task_desc.startswith("Start working on: "):
                task_desc = task_desc.replace("Start working on: ", "▶️ ")
            elif task_desc.startswith("Continue progress on: "):
                task_desc = task_desc.replace("Continue progress on: ", "⏭️ ")
            elif task_desc.startswith("Complete: "):
                task_desc = task_desc.replace("Complete: ", "✅ ")
            elif task_desc.startswith("Work on: "):
                task_desc = task_desc.replace("Work on: ", "🔨 ")
            
            option_text = f"{goal_title}: {task_desc} ({task.estimated_time_minutes}min)"
            options.append(Option(option_text, id=str(i)))
        
        yield Container(
            Static("Select a Task to Start:", classes="modal-title"),
            OptionList(*options, id="task-list"),
            Horizontal(
                Button("Start Task", variant="primary", id="start"),
                Button("Cancel", id="cancel"),
                Button("Quit", variant="error", id="quit"),
                classes="modal-buttons"
            ),
            classes="task-modal"
        )
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "start":
            self._start_selected_task()
        elif event.button.id == "cancel":
            self.dismiss(None)
        elif event.button.id == "quit":
            self.dismiss("quit")
    
    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle double-click or Enter on option list items"""
        self._start_selected_task()
    
    def _start_selected_task(self) -> None:
        """Start the currently selected task"""
        option_list = self.query_one("#task-list", OptionList)
        if option_list.highlighted is not None:
            selected_index = int(option_list.highlighted)
            _, selected_task = self.available_tasks[selected_index]
            self.dismiss(selected_task)


class AutoJournalTUI(App):
    """Main TUI application for AutoJournal"""
    
    TITLE = "AutoJournal - Productivity Tracker"
    
    # Disable mouse support to prevent mouse coordinate output
    ENABLE_COMMAND_PALETTE = False
    
    @property
    def mouse_captures(self) -> bool:
        """Disable mouse capture"""
        return False
    
    BINDINGS = [
        Binding("c", "mark_complete", "Complete Task"),
        Binding("e", "clarify_task", "Edit Task"),
        Binding("h", "hold_task", "Hold Task"),
        Binding("r", "resume_task", "Resume Task"),
        Binding("n", "pick_new_task", "New Task"),
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
    
    .task-modal {
        align: center middle;
        background: $surface;
        border: solid $accent;
        width: 80;
        height: 20;
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
        
        # Initialize notification manager
        self.notifier = NotificationManager(enabled=True)
    
    def _enable_mouse_support(self) -> bool:
        """Disable mouse support to prevent coordinate output"""
        return False
    
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
                yield Button("🔄 New Task (n)", id="new-task", variant="primary")
                yield Button("🏁 End Session (q)", id="quit", variant="error")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Set up the TUI when it starts"""
        # Disable mouse tracking sequences
        import sys
        sys.stdout.write('\033[?1000l')  # Disable basic mouse tracking
        sys.stdout.write('\033[?1003l')  # Disable all mouse tracking
        sys.stdout.write('\033[?1015l')  # Disable extended mouse tracking
        sys.stdout.write('\033[?1006l')  # Disable SGR mouse tracking
        sys.stdout.flush()
        
        self.set_interval(1.0, self.update_display)
        # Start monitoring loop in background
        screenshot_interval = get_setting("screenshot_interval")
        self.set_interval(float(screenshot_interval), self.take_screenshot_and_analyze)
        
        # Show task picker if no task is selected
        if not self.autojournal_app.current_task:
            self.call_after_refresh(self._show_initial_task_picker)
    
    def _show_initial_task_picker(self):
        """Show task picker on startup"""
        # Check if we have available tasks and show the picker
        # For now, use the blocking approach to get tasks
        try:
            # Use run_in_executor to run async code without creating conflicts
            import concurrent.futures
            import threading
            
            def get_tasks():
                # Run in a separate thread with its own event loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    tasks = loop.run_until_complete(
                        self.autojournal_app.goal_manager.get_all_available_tasks()
                    )
                    return tasks
                finally:
                    loop.close()
            
            # Get tasks in background thread
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(get_tasks)
                available_tasks = future.result(timeout=15)  # 15 second timeout for LLM calls
            
            if available_tasks:
                def handle_task_selection(selected_task):
                    if selected_task == "quit":
                        self.action_quit_app()  # Full quit
                    elif selected_task:
                        # Start the selected task in a thread
                        def start_task():
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            try:
                                loop.run_until_complete(
                                    self.autojournal_app.start_selected_task(selected_task)
                                )
                            except Exception as e:
                                # Log errors to debug file
                                debug_file = Path.home() / ".autojournal-debug.log"
                                with open(debug_file, "a") as f:
                                    from datetime import datetime
                                    timestamp = datetime.now().strftime("%H:%M:%S")
                                    f.write(f"{timestamp}: ERROR in start_task thread: {e}\n")
                                    import traceback
                                    traceback.print_exception(type(e), e, e.__traceback__, file=f)
                            finally:
                                loop.close()
                        
                        threading.Thread(target=start_task, daemon=True).start()
                        self.notify(f"Started task: {selected_task.description}")
                    else:
                        self.exit()  # Exit if no task selected
                
                self.show_task_picker(available_tasks, handle_task_selection)
            else:
                self.notify("No tasks available!")
                self.exit()
            
        except Exception as e:
            self.notify(f"Error loading tasks: {e}")
            self.exit()
    
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
        elif event.button.id == "new-task":
            self.action_pick_new_task()
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
    
    def action_pick_new_task(self) -> None:
        """Show task picker to select a new task"""
        try:
            # Use the same approach as initial task picker
            import concurrent.futures
            import threading
            
            def get_tasks():
                # Run in a separate thread with its own event loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(
                        self.autojournal_app.goal_manager.get_all_available_tasks()
                    )
                finally:
                    loop.close()
            
            # Get tasks in background thread
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(get_tasks)
                available_tasks = future.result(timeout=15)  # 15 second timeout for LLM calls
            
            if available_tasks:
                def handle_task_selection(selected_task):
                    if selected_task == "quit":
                        self.action_quit_app()  # Full quit
                    elif selected_task:
                        # Start the selected task in a thread
                        def start_task():
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            try:
                                loop.run_until_complete(
                                    self.autojournal_app.start_selected_task(selected_task)
                                )
                            except Exception as e:
                                # Log errors to debug file
                                debug_file = Path.home() / ".autojournal-debug.log"
                                with open(debug_file, "a") as f:
                                    from datetime import datetime
                                    timestamp = datetime.now().strftime("%H:%M:%S")
                                    f.write(f"{timestamp}: ERROR in start_new_task thread: {e}\n")
                                    import traceback
                                    traceback.print_exception(type(e), e, e.__traceback__, file=f)
                            finally:
                                loop.close()
                        
                        threading.Thread(target=start_task, daemon=True).start()
                        self.notify(f"Started new task: {selected_task.description}")
                    # If None (cancelled), just continue with current task
                
                self.show_task_picker(available_tasks, handle_task_selection)
            else:
                self.notify("No available tasks found!")
                
        except Exception as e:
            self.notify(f"Error loading tasks: {e}")
    
    def action_quit_app(self) -> None:
        """End session and quit application"""
        # Ensure mouse tracking is disabled before exit
        import sys
        sys.stdout.write('\033[?1000l')  # Disable basic mouse tracking
        sys.stdout.write('\033[?1003l')  # Disable all mouse tracking
        sys.stdout.write('\033[?1015l')  # Disable extended mouse tracking
        sys.stdout.write('\033[?1006l')  # Disable SGR mouse tracking
        sys.stdout.flush()
        
        # Clean up current task file
        self._cleanup_current_task_file()
        
        asyncio.create_task(self.autojournal_app.end_session())
        self.exit()
    
    def _cleanup_current_task_file(self) -> None:
        """Clear the current task file"""
        try:
            current_task_file = Path.home() / ".current-task"
            current_task_file.write_text("")
        except Exception as e:
            print(f"Error clearing current task file: {e}")
    
    def take_screenshot_and_analyze(self) -> None:
        """Take screenshot and analyze activity (called by timer)"""
        try:
            # Add debug logging
            debug_file = Path.home() / ".autojournal-debug.log"
            with open(debug_file, "a") as f:
                from datetime import datetime
                timestamp = datetime.now().strftime("%H:%M:%S")
                f.write(f"{timestamp}: take_screenshot_and_analyze called\n")
            
            # Use asyncio.create_task to run in the existing event loop
            import asyncio
            
            async def run_analysis():
                analysis = await self.autojournal_app.screenshot_analyzer.analyze_current_activity(
                    self.autojournal_app.current_task,
                    self.autojournal_app.journal_manager.get_recent_entries()
                )
                
                # Send notification if user is off-task
                if not analysis.is_on_task and self.autojournal_app.current_task:
                    current_activity = f"{analysis.description} (using {analysis.current_app})"
                    expected_task = self.autojournal_app.current_task.description
                    
                    # Send notification in a separate thread to avoid blocking
                    import threading
                    
                    def send_notification():
                        try:
                            self.notifier.notify_off_task(current_activity, expected_task)
                        except Exception as e:
                            # Log notification errors but don't crash
                            debug_file = Path.home() / ".autojournal-debug.log"
                            with open(debug_file, "a") as f:
                                from datetime import datetime
                                timestamp = datetime.now().strftime("%H:%M:%S")
                                f.write(f"{timestamp}: Notification error: {e}\n")
                    
                    threading.Thread(target=send_notification, daemon=True).start()
                
                # Log the analysis
                await self.autojournal_app.journal_manager.log_activity(analysis)
                return analysis
            
            # Schedule the analysis to run in the existing event loop
            asyncio.create_task(run_analysis())
            
            # Log that we scheduled the analysis
            with open(debug_file, "a") as f:
                timestamp = datetime.now().strftime("%H:%M:%S")
                f.write(f"{timestamp}: screenshot analysis scheduled\n")
            
        except Exception as e:
            # Don't crash the TUI if analysis fails
            debug_file = Path.home() / ".autojournal-debug.log"
            with open(debug_file, "a") as f:
                from datetime import datetime
                timestamp = datetime.now().strftime("%H:%M:%S")
                f.write(f"{timestamp}: Analysis error: {e}\n")
                import traceback
                traceback.print_exception(type(e), e, e.__traceback__, file=f)
            print(f"Analysis error: {e}")
    
    def show_task_picker(self, available_tasks: list, callback):
        """Show task selection modal"""
        self.push_screen(TaskSelectionModal(available_tasks), callback)
    
    def run_app(self):
        """Run the TUI application"""
        return self.run()