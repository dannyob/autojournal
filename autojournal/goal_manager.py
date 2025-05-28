"""Goal management and AI-powered goal breakdown"""

import re
import subprocess
import json
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from .models import Goal, Task, TaskStatus, JournalEntry


class GoalManager:
    """Manages goals, breaks them down into tasks, and provides AI analysis"""
    
    def __init__(self):
        self.goals: List[Goal] = []
        self.current_goal_index = 0
    
    def load_goals(self, goals_file: Path) -> List[Goal]:
        """Load goals from a markdown file"""
        try:
            content = goals_file.read_text()
            goals = self._parse_markdown_goals(content)
            self.goals = goals
            return goals
        except Exception as e:
            print(f"Error loading goals: {e}")
            return []
    
    def _parse_markdown_goals(self, content: str) -> List[Goal]:
        """Parse goals from markdown content"""
        goals = []
        
        # Split by headers (# or ## or ###)
        sections = re.split(r'\n#+\s+', content)
        
        for section in sections[1:]:  # Skip first empty section
            lines = section.strip().split('\n')
            if not lines:
                continue
                
            title = lines[0].strip()
            description = '\n'.join(lines[1:]).strip() if len(lines) > 1 else title
            
            goal = Goal(title=title, description=description)
            goals.append(goal)
        
        return goals
    
    async def break_down_goal(self, goal: Goal) -> List[Task]:
        """Use LLM to break down a goal into actionable sub-tasks"""
        prompt = f"""
Break down this goal into 3-5 specific, actionable sub-tasks that can be completed in 15-60 minutes each.

Goal: {goal.title}
Description: {goal.description}

For each sub-task, provide:
1. A clear, specific description of what needs to be done
2. Estimated time in minutes

Format your response as JSON with this structure:
{{
    "tasks": [
        {{
            "description": "Specific task description",
            "estimated_time_minutes": 30
        }}
    ]
}}
"""
        
        try:
            # Use llm command line tool
            result = subprocess.run(
                ['llm', prompt],
                capture_output=True,
                text=True,
                check=True
            )
            
            response_data = json.loads(result.stdout.strip())
            tasks = []
            
            for task_data in response_data.get('tasks', []):
                task = Task(
                    description=task_data['description'],
                    estimated_time_minutes=task_data['estimated_time_minutes']
                )
                tasks.append(task)
            
            goal.sub_tasks = tasks
            return tasks
            
        except Exception as e:
            print(f"Error breaking down goal: {e}")
            # Fallback: create a single task from the goal
            fallback_task = Task(
                description=f"Work on: {goal.title}",
                estimated_time_minutes=45
            )
            goal.sub_tasks = [fallback_task]
            return [fallback_task]
    
    def get_next_task(self) -> Optional[Task]:
        """Get the next pending task"""
        for goal in self.goals:
            for task in goal.sub_tasks:
                if task.status == TaskStatus.PENDING:
                    return task
        return None
    
    async def generate_session_summary(self, journal_entries: List[JournalEntry]) -> str:
        """Generate an AI-powered summary of the session with efficiency insights"""
        
        if not journal_entries:
            return "No activity recorded during this session."
        
        # Prepare journal content for analysis
        journal_text = ""
        for entry in journal_entries:
            journal_text += f"[{entry.timestamp.strftime('%H:%M:%S')}] {entry.content}\n"
        
        prompt = f"""
Analyze this productivity session and provide insights on efficiency and recommendations for improvement.

Session Journal:
{journal_text}

Provide a summary that includes:
1. Overview of what was accomplished
2. Time spent on-task vs off-task
3. Main distractions or productivity killers
4. Recommendations for improving focus and efficiency
5. Overall productivity rating (1-10)

Keep the summary concise but actionable.
"""
        
        try:
            result = subprocess.run(
                ['llm', prompt],
                capture_output=True,
                text=True,
                check=True
            )
            
            return result.stdout.strip()
            
        except Exception as e:
            return f"Error generating summary: {e}"