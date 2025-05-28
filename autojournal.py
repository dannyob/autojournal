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
        """Initialize the session by loading goals and setting up the first task"""
        if not self.goals_file.exists():
            print(f"Goals file '{self.goals_file}' not found!")
            sys.exit(1)
            
        goals = self.goal_manager.load_goals(self.goals_file)
        if not goals:
            print("No goals found in goals file!")
            sys.exit(1)
            
        # Break down the first goal into sub-tasks
        first_goal = goals[0]
        sub_tasks = await self.goal_manager.break_down_goal(first_goal)
        
        if sub_tasks:
            self.current_task = sub_tasks[0]
            self.journal_manager.set_current_task(self.current_task)
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
            await self.journal_manager.log_task_completion(self.current_task)
            # TODO: Get next task from goal manager
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
            await self.journal_manager.log_task_hold(self.current_task, reason)
    
    async def resume_task(self):
        """Resume the current task from hold"""
        if self.current_task:
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
    
    args = parser.parse_args()
    
    app = AutoJournal(args.goals_file)
    
    try:
        # Create a new event loop for the entire application
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Initialize the app
        loop.run_until_complete(app.initialize())
        
        # Run the TUI (this blocks until quit)
        # The monitoring loop will run in the background via TUI updates
        app.tui.run()
        
        loop.close()
        
    except KeyboardInterrupt:
        print("\nSession interrupted")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()