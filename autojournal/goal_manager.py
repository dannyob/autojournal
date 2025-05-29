"""Goal management and AI-powered goal breakdown"""

import re
import json
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime

try:
    import llm
except ImportError:
    llm = None

from .models import Goal, Task, TaskStatus, JournalEntry
from .config import get_model, get_prompt

# Set up debug logging
debug_logger = logging.getLogger('autojournal.debug')
debug_logger.setLevel(logging.DEBUG)
if not debug_logger.handlers:
    debug_handler = logging.FileHandler('.autojournal-debug.log')
    debug_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    debug_handler.setFormatter(formatter)
    debug_logger.addHandler(debug_handler)


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
        debug_logger.debug(f"break_down_goal: Starting breakdown for goal '{goal.title}'")
        
        # Get prompt from configuration and format it
        debug_logger.debug("break_down_goal: Getting prompt template")
        try:
            prompt_template = get_prompt("goal_breakdown")
            debug_logger.debug(f"break_down_goal: Got prompt template, length: {len(prompt_template)}")
        except Exception as e:
            debug_logger.error(f"break_down_goal: Error getting prompt template: {e}")
            raise
        
        debug_logger.debug("break_down_goal: Formatting prompt")
        try:
            prompt = prompt_template.format(
                goal_title=goal.title,
                goal_description=goal.description
            )
            debug_logger.debug(f"break_down_goal: Formatted prompt, length: {len(prompt)}")
        except Exception as e:
            debug_logger.error(f"break_down_goal: Error formatting prompt: {e}")
            raise
        
        try:
            debug_logger.debug("break_down_goal: Checking if llm library is available")
            if llm is None:
                debug_logger.error("break_down_goal: llm library not available")
                raise ImportError("llm library not available")
            
            debug_logger.debug("break_down_goal: llm library is available")
            
            # Use the llm Python library with configured model
            try:
                # Try to use configured model for goal breakdown
                debug_logger.debug("break_down_goal: Getting model name for goal_breakdown")
                model_name = get_model("goal_breakdown")
                debug_logger.debug(f"break_down_goal: Got model name: {model_name}")
                
                debug_logger.debug("break_down_goal: Getting LLM model instance")
                model = llm.get_model(model_name)
                debug_logger.debug(f"break_down_goal: Got model instance: {type(model)}")
                
                debug_logger.debug("break_down_goal: About to call model.prompt() - THIS IS WHERE HANG MIGHT OCCUR")
                response = model.prompt(prompt)
                debug_logger.debug("break_down_goal: model.prompt() returned successfully")
                
                debug_logger.debug("break_down_goal: Getting response text")
                response_text = response.text()
                debug_logger.debug(f"break_down_goal: Got response text, length: {len(response_text)}")
                
            except Exception as model_error:
                debug_logger.error(f"break_down_goal: LLM model error: {model_error}")
                print(f"LLM model error: {model_error}")
                # Try with fallback model
                try:
                    debug_logger.debug("break_down_goal: Trying fallback model")
                    fallback_model = get_model("fallback")
                    debug_logger.debug(f"break_down_goal: Got fallback model name: {fallback_model}")
                    
                    model = llm.get_model(fallback_model)
                    debug_logger.debug(f"break_down_goal: Got fallback model instance: {type(model)}")
                    
                    debug_logger.debug("break_down_goal: About to call fallback model.prompt() - THIS IS WHERE HANG MIGHT OCCUR")
                    response = model.prompt(prompt)
                    debug_logger.debug("break_down_goal: Fallback model.prompt() returned successfully")
                    
                    response_text = response.text()
                    debug_logger.debug(f"break_down_goal: Got fallback response text, length: {len(response_text)}")
                    
                except Exception as fallback_error:
                    debug_logger.error(f"break_down_goal: LLM fallback error: {fallback_error}")
                    print(f"LLM fallback error: {fallback_error}")
                    raise model_error
            
            debug_logger.debug("break_down_goal: Processing LLM response")
            # Try to extract JSON from the response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                debug_logger.debug("break_down_goal: Found JSON in response")
                json_text = json_match.group()
                debug_logger.debug(f"break_down_goal: Extracted JSON text, length: {len(json_text)}")
                response_data = json.loads(json_text)
                debug_logger.debug(f"break_down_goal: Parsed JSON successfully, keys: {list(response_data.keys())}")
            else:
                debug_logger.error("break_down_goal: No JSON found in response")
                raise ValueError("No JSON found in response")
            
            debug_logger.debug("break_down_goal: Creating Task objects from response")
            tasks = []
            
            for i, task_data in enumerate(response_data.get('tasks', [])):
                debug_logger.debug(f"break_down_goal: Processing task {i+1}: {task_data.get('description', 'N/A')}")
                task = Task(
                    description=task_data['description'],
                    estimated_time_minutes=task_data.get('estimated_minutes', 30)  # Use 'estimated_minutes' from LLM response
                )
                tasks.append(task)
            
            debug_logger.debug(f"break_down_goal: Created {len(tasks)} tasks")
            goal.sub_tasks = tasks
            debug_logger.debug("break_down_goal: Successfully completed goal breakdown")
            return tasks
            
        except Exception as e:
            debug_logger.error(f"break_down_goal: Error breaking down goal: {e}")
            print(f"Error breaking down goal: {e}")
            # Fallback: create sub-tasks based on goal content
            debug_logger.debug("break_down_goal: Using fallback task creation")
            fallback_tasks = self._create_fallback_tasks(goal)
            goal.sub_tasks = fallback_tasks
            debug_logger.debug(f"break_down_goal: Created {len(fallback_tasks)} fallback tasks")
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
        debug_logger.debug(f"get_all_available_tasks: Starting with {len(self.goals)} goals")
        all_tasks = []
        
        for i, goal in enumerate(self.goals):
            debug_logger.debug(f"get_all_available_tasks: Processing goal {i+1}/{len(self.goals)}: '{goal.title}'")
            debug_logger.debug(f"get_all_available_tasks: Goal has {len(goal.sub_tasks)} existing sub-tasks")
            
            # If goal doesn't have sub-tasks yet, break it down
            if not goal.sub_tasks:
                debug_logger.debug(f"get_all_available_tasks: Goal '{goal.title}' has no sub-tasks, breaking down")
                try:
                    await self.break_down_goal(goal)
                    debug_logger.debug(f"get_all_available_tasks: Successfully broke down goal '{goal.title}', now has {len(goal.sub_tasks)} sub-tasks")
                except Exception as e:
                    debug_logger.error(f"get_all_available_tasks: Error breaking down goal '{goal.title}': {e}")
                    continue
            else:
                debug_logger.debug(f"get_all_available_tasks: Goal '{goal.title}' already has sub-tasks, skipping breakdown")
            
            # Add all pending tasks from this goal
            pending_count = 0
            for task in goal.sub_tasks:
                if task.status == TaskStatus.PENDING:
                    all_tasks.append((goal.title, task))
                    pending_count += 1
            
            debug_logger.debug(f"get_all_available_tasks: Added {pending_count} pending tasks from goal '{goal.title}'")
        
        debug_logger.debug(f"get_all_available_tasks: Total tasks collected: {len(all_tasks)}")
        
        # Remove any duplicate tasks (same description and goal)
        debug_logger.debug("get_all_available_tasks: Removing duplicate tasks")
        seen = set()
        unique_tasks = []
        for goal_title, task in all_tasks:
            task_key = (goal_title, task.description, task.estimated_time_minutes)
            if task_key not in seen:
                seen.add(task_key)
                unique_tasks.append((goal_title, task))
        
        debug_logger.debug(f"get_all_available_tasks: After deduplication: {len(unique_tasks)} unique tasks")
        debug_logger.debug("get_all_available_tasks: Finished successfully")
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
        debug_logger.debug(f"generate_session_summary: Starting with {len(journal_entries)} journal entries")
        
        if not journal_entries:
            debug_logger.debug("generate_session_summary: No journal entries, returning default message")
            return "No activity recorded during this session."
        
        # Prepare journal content for analysis
        debug_logger.debug("generate_session_summary: Preparing activity summary")
        activity_summary = ""
        for entry in journal_entries:
            activity_summary += f"[{entry.timestamp.strftime('%H:%M:%S')}] {entry.content}\n"
        debug_logger.debug(f"generate_session_summary: Activity summary length: {len(activity_summary)}")
        
        # Prepare task context
        debug_logger.debug("generate_session_summary: Preparing task context")
        task_context = ""
        if journal_entries and journal_entries[0].task_context:
            task = journal_entries[0].task_context
            task_context = f"Task: {task.description} (estimated {task.estimated_time_minutes} min)"
            debug_logger.debug(f"generate_session_summary: Task context: {task_context}")
        else:
            debug_logger.debug("generate_session_summary: No task context available")
        
        # Get prompt from configuration and format it
        debug_logger.debug("generate_session_summary: Getting prompt template")
        try:
            prompt_template = get_prompt("session_summary")
            debug_logger.debug(f"generate_session_summary: Got prompt template, length: {len(prompt_template)}")
            
            prompt = prompt_template.format(
                task_context=task_context,
                activity_summary=activity_summary
            )
            debug_logger.debug(f"generate_session_summary: Formatted prompt, length: {len(prompt)}")
        except Exception as e:
            debug_logger.error(f"generate_session_summary: Error with prompt: {e}")
            return f"Error preparing prompt: {e}"
        
        try:
            debug_logger.debug("generate_session_summary: Checking LLM availability")
            if llm is None:
                debug_logger.error("generate_session_summary: LLM library not available")
                return "LLM library not available for summary generation"
            
            debug_logger.debug("generate_session_summary: Getting model for session summary")
            model_name = get_model("session_summary")
            debug_logger.debug(f"generate_session_summary: Got model name: {model_name}")
            
            model = llm.get_model(model_name)
            debug_logger.debug(f"generate_session_summary: Got model instance: {type(model)}")
            
            debug_logger.debug("generate_session_summary: About to call model.prompt() for summary")
            response = model.prompt(prompt)
            debug_logger.debug("generate_session_summary: model.prompt() returned successfully")
            
            result = response.text()
            debug_logger.debug(f"generate_session_summary: Got summary text, length: {len(result)}")
            return result
            
        except Exception as e:
            debug_logger.error(f"generate_session_summary: Error generating summary: {e}")
            return f"Error generating summary: {e}"