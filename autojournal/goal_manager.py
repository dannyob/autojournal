"""Goal management and AI-powered goal breakdown"""

import re
import json
from pathlib import Path
from typing import List, Optional
from datetime import datetime

try:
    import llm
except ImportError:
    llm = None

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
        prompt = f"""Break down this goal into 3-5 specific, actionable sub-tasks that can be completed in 15-60 minutes each.

Goal: {goal.title}
Description: {goal.description}

Respond with ONLY valid JSON in this exact format:
{{
    "tasks": [
        {{
            "description": "Specific task description",
            "estimated_time_minutes": 30
        }}
    ]
}}"""
        
        try:
            if llm is None:
                raise ImportError("llm library not available")
            
            # Use the llm Python library with default model
            try:
                model = llm.get_model()  # Use default model
                response = model.prompt(prompt)
                response_text = response.text()
            except Exception as model_error:
                print(f"LLM model error: {model_error}")
                raise model_error
            
            # Try to extract JSON from the response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_text = json_match.group()
                response_data = json.loads(json_text)
            else:
                raise ValueError("No JSON found in response")
            
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
            # Fallback: create sub-tasks based on goal content
            fallback_tasks = self._create_fallback_tasks(goal)
            goal.sub_tasks = fallback_tasks
            return fallback_tasks
    
    def _create_fallback_tasks(self, goal: Goal) -> List[Task]:
        """Create fallback tasks when LLM fails"""
        if not goal.description or goal.description == goal.title:
            # Simple goal, create basic tasks
            return [
                Task(f"Start working on: {goal.title}", 30),
                Task(f"Continue progress on: {goal.title}", 30),
                Task(f"Complete: {goal.title}", 30)
            ]
        else:
            # Try to break down based on content
            sentences = goal.description.split('.')
            tasks = []
            
            # Create tasks based on sentences or use defaults
            if len(sentences) > 1:
                for i, sentence in enumerate(sentences[:5]):
                    if sentence.strip():
                        tasks.append(Task(
                            f"Work on: {sentence.strip()[:50]}...",
                            30 + (i * 10)  # Varying time estimates
                        ))
            
            if not tasks:
                tasks = [Task(f"Work on: {goal.title}", 45)]
            
            return tasks
    
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
            if llm is None:
                return "LLM library not available for summary generation"
            
            model = llm.get_model()
            response = model.prompt(prompt)
            return response.text()
            
        except Exception as e:
            return f"Error generating summary: {e}"