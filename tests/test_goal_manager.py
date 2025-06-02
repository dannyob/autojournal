"""Tests for GoalManager"""

import tempfile
from pathlib import Path
from autojournal.goal_manager import GoalManager
from autojournal.models import Goal, Task, TaskStatus


class TestGoalManager:
    def setup_method(self):
        self.goal_manager = GoalManager()
    
    def test_parse_simple_markdown_goals(self):
        markdown_content = """
# Goal 1
This is the first goal description.

# Goal 2
This is the second goal description.
It has multiple lines.

# Goal 3
Simple goal without description.
"""
        goals = self.goal_manager._parse_markdown_goals(markdown_content)
        
        assert len(goals) == 3
        assert goals[0].title == "Goal 1"
        assert goals[0].description == "This is the first goal description."
        assert goals[1].title == "Goal 2"
        assert "multiple lines" in goals[1].description
        assert goals[2].title == "Goal 3"
    
    def test_parse_markdown_with_different_headers(self):
        markdown_content = """
## Main Goal
Description for main goal.

### Sub Goal
Description for sub goal.
"""
        goals = self.goal_manager._parse_markdown_goals(markdown_content)
        
        assert len(goals) == 2
        assert goals[0].title == "Main Goal"
        assert goals[1].title == "Sub Goal"
    
    def test_load_goals_from_file(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("""
# Test Goal 1
Complete the first test goal.

# Test Goal 2
Complete the second test goal.
""")
            temp_path = Path(f.name)
        
        try:
            goals = self.goal_manager.load_goals(temp_path)
            
            assert len(goals) == 2
            assert goals[0].title == "Test Goal 1"
            assert goals[1].title == "Test Goal 2"
            assert self.goal_manager.goals == goals
        finally:
            temp_path.unlink()
    
    def test_load_nonexistent_file(self):
        fake_path = Path("nonexistent_file.md")
        goals = self.goal_manager.load_goals(fake_path)
        
        assert goals == []
        assert self.goal_manager.goals == []
    
    def test_get_next_task(self):
        # Create goals with tasks
        goal1 = Goal("Goal 1", "First goal")
        task1 = Task("Task 1", 30, status=TaskStatus.COMPLETED)
        task2 = Task("Task 2", 45, status=TaskStatus.PENDING)
        goal1.sub_tasks = [task1, task2]
        
        goal2 = Goal("Goal 2", "Second goal")
        task3 = Task("Task 3", 60, status=TaskStatus.PENDING)
        goal2.sub_tasks = [task3]
        
        self.goal_manager.goals = [goal1, goal2]
        
        next_task = self.goal_manager.get_next_task()
        
        assert next_task == task2  # First pending task
    
    def test_get_next_task_no_pending(self):
        goal = Goal("Goal 1", "First goal")
        task = Task("Task 1", 30, status=TaskStatus.COMPLETED)
        goal.sub_tasks = [task]
        
        self.goal_manager.goals = [goal]
        
        next_task = self.goal_manager.get_next_task()
        
        assert next_task is None
    
    def test_empty_goals_list(self):
        next_task = self.goal_manager.get_next_task()
        assert next_task is None