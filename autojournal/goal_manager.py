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
from .config import get_model


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
        """Parse goals from markdown content with sub-tasks"""
        goals = []
        
        # Split by top-level headers only (# not ## or ###)
        # Handle case where first goal doesn't have leading newline
        if content.startswith('# '):
            content = '\n' + content
        
        sections = re.split(r'\n# ', content)
        
        for section in sections[1:]:  # Skip first empty section
            lines = section.strip().split('\n')
            if not lines:
                continue
                
            title = lines[0].strip()
            
            # Find description and sub-tasks
            description_lines = []
            tasks = []
            
            i = 1
            # Collect description until we hit checkboxes or end
            while i < len(lines):
                line = lines[i].strip()
                if line.startswith('- [ ]') or line.startswith('- [x]') or line.startswith('- [X]'):
                    break
                if line:  # Only add non-empty lines
                    description_lines.append(line)
                i += 1
            
            # Collect sub-tasks from checkboxes
            while i < len(lines):
                line = lines[i].strip()
                if line.startswith('- [ ]'):
                    # Pending task
                    task_desc = line[5:].strip()  # Remove '- [ ] '
                    if task_desc:
                        task = Task(task_desc, 30)  # Default 30 min
                        task.status = TaskStatus.PENDING
                        tasks.append(task)
                elif line.startswith('- [x]') or line.startswith('- [X]'):
                    # Completed task
                    task_desc = line[5:].strip()  # Remove '- [x] '
                    if task_desc:
                        task = Task(task_desc, 30)  # Default 30 min
                        task.status = TaskStatus.COMPLETED
                        task.progress_percentage = 100
                        tasks.append(task)
                i += 1
            
            description = '\n'.join(description_lines).strip()
            if not description:
                description = title
                
            goal = Goal(title=title, description=description)
            goal.sub_tasks = tasks
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
            
            # Use the llm Python library with configured model
            try:
                # Try to use configured model for goal breakdown
                model_name = get_model("goal_breakdown")
                model = llm.get_model(model_name)
                response = model.prompt(prompt)
                response_text = response.text()
            except Exception as model_error:
                print(f"LLM model error: {model_error}")
                # Try with fallback model
                try:
                    fallback_model = get_model("fallback")
                    model = llm.get_model(fallback_model)
                    response = model.prompt(prompt)
                    response_text = response.text()
                except Exception as fallback_error:
                    print(f"LLM fallback error: {fallback_error}")
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
    
    async def get_all_available_tasks(self) -> List[tuple]:
        """Get all available tasks from all goals as (goal_title, task) tuples"""
        all_tasks = []
        
        for goal in self.goals:
            # If goal doesn't have sub-tasks yet, break it down
            if not goal.sub_tasks:
                await self.break_down_goal(goal)
            
            # Add all pending tasks from this goal
            for task in goal.sub_tasks:
                if task.status == TaskStatus.PENDING:
                    all_tasks.append((goal.title, task))
        
        # Remove any duplicate tasks (same description and goal)
        seen = set()
        unique_tasks = []
        for goal_title, task in all_tasks:
            task_key = (goal_title, task.description, task.estimated_time_minutes)
            if task_key not in seen:
                seen.add(task_key)
                unique_tasks.append((goal_title, task))
        
        return unique_tasks
    
    def get_all_tasks_with_status(self) -> List[tuple]:
        """Get all tasks with their current status for debugging"""
        all_tasks = []
        for goal in self.goals:
            for task in goal.sub_tasks:
                all_tasks.append((goal.title, task, task.status.value))
        return all_tasks
    
    def mark_task_complete(self, completed_task: Task) -> bool:
        """Mark a specific task as complete in the goals list"""
        for goal in self.goals:
            for task in goal.sub_tasks:
                if (task.description == completed_task.description and 
                    task.estimated_time_minutes == completed_task.estimated_time_minutes):
                    task.status = TaskStatus.COMPLETED
                    task.progress_percentage = 100
                    return True
        return False
    
    def update_task_status(self, target_task: Task, new_status: TaskStatus) -> bool:
        """Update a specific task's status in the goals list"""
        for goal in self.goals:
            for task in goal.sub_tasks:
                if (task.description == target_task.description and 
                    task.estimated_time_minutes == target_task.estimated_time_minutes):
                    task.status = new_status
                    return True
        return False
    
    def save_goals_to_file(self, goals_file: Path) -> None:
        """Save goals with task status back to markdown file using checkbox format"""
        try:
            content = []
            
            for goal in self.goals:
                # Add goal header
                content.append(f"# {goal.title}")
                content.append("")
                
                # Add goal description if different from title
                if goal.description and goal.description != goal.title:
                    content.append(goal.description)
                    content.append("")
                
                # Add sub-tasks if they exist
                if goal.sub_tasks:
                    for task in goal.sub_tasks:
                        # Use checkbox format based on status
                        if task.status == TaskStatus.COMPLETED:
                            checkbox = "[x]"
                        else:
                            checkbox = "[ ]"
                        
                        task_line = f"- {checkbox} {task.description}"
                        content.append(task_line)
                    content.append("")
            
            # Write to file
            goals_file.write_text("\n".join(content), encoding='utf-8')
            
        except Exception as e:
            print(f"Error saving goals to file: {e}")
    
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
            
            model_name = get_model("session_summary")
            model = llm.get_model(model_name)
            response = model.prompt(prompt)
            return response.text()
            
        except Exception as e:
            return f"Error generating summary: {e}"