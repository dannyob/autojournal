#!/usr/bin/env python3
"""
AutoJournal - An intelligent productivity tracking system
"""

import asyncio
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Optional

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from autojournal.goal_manager import GoalManager
from autojournal.journal_manager import JournalManager
from autojournal.screenshot_analyzer import ScreenshotAnalyzer
from autojournal.tui import AutoJournalTUI


class AutoJournal:
    def __init__(self, goals_file: str = "goals.md"):
        self.goals_file = Path(goals_file)
        self.goal_manager = GoalManager()
        self.journal_manager = JournalManager()
        self.screenshot_analyzer = ScreenshotAnalyzer()
        self.tui = AutoJournalTUI(self)
        self.current_task = None
        self.running = False
        
    async def initialize(self):
        """Initialize the session by loading goals"""
        if not self.goals_file.exists():
            print(f"Goals file '{self.goals_file}' not found!")
            sys.exit(1)
            
        goals = self.goal_manager.load_goals(self.goals_file)
        if not goals:
            print("No goals found in goals file!")
            sys.exit(1)
    
    async def start_selected_task(self, selected_task: 'Task'):
        """Start the selected task"""
        self.current_task = selected_task
        
        # Update task status in goals list
        from autojournal.models import TaskStatus
        self.goal_manager.update_task_status(self.current_task, TaskStatus.IN_PROGRESS)
        
        # Save updated goals to file
        self.goal_manager.save_goals_to_file(self.goals_file)
        
        # Set current task in journal manager - this should write to ~/.current-task
        self.journal_manager.set_current_task(self.current_task)
        
        # Force update of current task display to ensure file is written
        self.journal_manager._update_current_task_display()
        
        await self.journal_manager.log_task_start(self.current_task)
        
    async def run_monitoring_loop(self):
        """Main monitoring loop that takes screenshots and analyzes activity"""
        self.running = True
        
        while self.running:
            try:
                # Take screenshot and analyze
                analysis = await self.screenshot_analyzer.analyze_current_activity(
                    self.current_task,
                    self.journal_manager.get_recent_entries()
                )
                
                # Log the analysis to journal
                await self.journal_manager.log_activity(analysis)
                
                # Wait 10 seconds before next screenshot
                await asyncio.sleep(10)
                
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
                await asyncio.sleep(10)
    
    async def mark_task_complete(self):
        """Mark current task as complete and move to next"""
        if self.current_task:
            # Mark task as complete in goals list
            self.goal_manager.mark_task_complete(self.current_task)
            
            # Save updated goals to file
            self.goal_manager.save_goals_to_file(self.goals_file)
            
            # Log completion to journal
            await self.journal_manager.log_task_completion(self.current_task)
            
            print("Task marked as complete!")
    
    async def clarify_task(self, new_description: str):
        """Update the current task description"""
        if self.current_task:
            old_desc = self.current_task.description
            self.current_task.description = new_description
            self.journal_manager.set_current_task(self.current_task)
            await self.journal_manager.log_task_clarification(old_desc, new_description)
    
    async def put_task_on_hold(self, reason: str = "Break"):
        """Temporarily pause the current task"""
        if self.current_task:
            # Update task status in goals list
            from autojournal.models import TaskStatus
            self.goal_manager.update_task_status(self.current_task, TaskStatus.ON_HOLD)
            
            # Save updated goals to file
            self.goal_manager.save_goals_to_file(self.goals_file)
            
            await self.journal_manager.log_task_hold(self.current_task, reason)
    
    async def resume_task(self):
        """Resume the current task from hold"""
        if self.current_task:
            # Update task status in goals list
            from autojournal.models import TaskStatus
            self.goal_manager.update_task_status(self.current_task, TaskStatus.IN_PROGRESS)
            
            # Save updated goals to file
            self.goal_manager.save_goals_to_file(self.goals_file)
            
            await self.journal_manager.log_task_resume(self.current_task)
    
    async def end_session(self):
        """End the session and generate summary"""
        self.running = False
        if self.current_task:
            await self.journal_manager.log_session_end()
        
        # Generate efficiency summary
        summary = await self.goal_manager.generate_session_summary(
            self.journal_manager.get_all_entries()
        )
        
        print("\n=== Session Summary ===")
        print(summary)
        
    def stop(self):
        """Stop the monitoring loop"""
        self.running = False


def main():
    parser = argparse.ArgumentParser(description="AutoJournal - Intelligent productivity tracking")
    parser.add_argument("goals_file", nargs="?", default="goals.md", 
                       help="Path to goals markdown file (default: goals.md)")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    
    args = parser.parse_args()
    
    if args.debug:
        print(f"[DEBUG] Starting AutoJournal with goals file: {args.goals_file}")
    
    app = AutoJournal(args.goals_file)
    
    try:
        if args.debug:
            print("[DEBUG] Creating event loop...")
        
        # Create a new event loop for the entire application
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        if args.debug:
            print("[DEBUG] Initializing application...")
        
        # Initialize the app
        loop.run_until_complete(app.initialize())
        
        if args.debug:
            print("[DEBUG] Starting TUI...")
        
        # Run the TUI (this blocks until quit)
        # The monitoring loop will run in the background via TUI updates
        # Configure to disable mouse tracking
        import os
        os.environ.setdefault('TEXTUAL_NO_MOUSE', '1')
        app.tui.run()
        
        if args.debug:
            print("[DEBUG] TUI exited normally")
        
        loop.close()
        
    except KeyboardInterrupt:
        print("\n[DEBUG] Session interrupted by user")
    except Exception as e:
        print(f"[ERROR] Unhandled exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if args.debug:
            print("[DEBUG] Cleaning up...")
        
        # Clean up current task file
        try:
            current_task_file = Path.home() / ".current-task"
            current_task_file.write_text("")
            if args.debug:
                print("[DEBUG] Cleared current task file")
        except Exception as e:
            if args.debug:
                print(f"[DEBUG] Error clearing current task file: {e}")
        
        # Ensure mouse tracking is disabled when exiting
        import sys
        sys.stdout.write('\033[?1000l')  # Disable basic mouse tracking
        sys.stdout.write('\033[?1003l')  # Disable all mouse tracking  
        sys.stdout.write('\033[?1015l')  # Disable extended mouse tracking
        sys.stdout.write('\033[?1006l')  # Disable SGR mouse tracking
        sys.stdout.flush()
        
        if args.debug:
            print("[DEBUG] Cleanup complete")


if __name__ == "__main__":
    main()