# AutoJournal

An intelligent productivity tracking system that monitors your daily progress towards goals through automated screen analysis and journaling.

## Overview

AutoJournal helps you stay focused and productive by:

1. **Goal Management**: Reads daily goals from a markdown file and breaks them into actionable sub-goals
2. **Automated Tracking**: Takes screenshots every 10 seconds and uses AI to analyze your current activity
3. **Smart Journaling**: Maintains a timestamped journal of your progress, noting what you're doing and how it relates to your goals
4. **Interactive TUI**: Provides a terminal interface to manage tasks, mark completion, clarify goals, or take breaks
5. **Efficiency Analysis**: Summarizes your session and provides insights for improvement

## How It Works

1. **Initialize**: The program reads your daily goals from a markdown file
2. **Goal Breakdown**: AI breaks down goals into manageable sub-tasks
3. **Task Selection**: Picks the first sub-task and displays it in `~/.current-task` (for screen display)
4. **Continuous Monitoring**: Every 10 seconds:
   - Takes a screenshot
   - Analyzes what you're doing using LLM
   - Updates the journal with activity description, current app, and progress estimate
5. **Interactive Control**: TUI allows you to:
   - Mark tasks as complete
   - Clarify/rewrite task descriptions
   - Put tasks on hold (for breaks)
   - End session with summary and efficiency recommendations

## Features

- **AI-Powered Analysis**: Uses Simon Willison's `llm` library with your default model
- **Real-time Display**: Current task shown in `~/.current-task` for external display systems
- **Daily Journaling**: Automatic markdown journal creation with timestamps
- **Progress Tracking**: Estimates completion percentage for ongoing tasks
- **Distraction Detection**: Identifies when you're off-task and logs accordingly
- **Session Summaries**: End-of-session analysis with productivity insights

## Requirements

- Python 3.8+
- `llm` library (Simon Willison's LLM tool)
- Screen capture capabilities
- Terminal support for TUI

## Installation

```bash
uv add llm textual pillow
```

## Usage

```bash
uv run python autojournal.py [goals_file.md]
```

If no goals file is specified, the program will look for `goals.md` in the current directory.

## File Structure

- `goals.md` - Your daily goals in markdown format
- `~/.current-task` - Current task display file
- Journal files are created as `journal-YYYY-MM-DD.md` in the current directory

## Development

This project includes comprehensive unit tests and follows TDD principles. Run tests with:

```bash
uv run python -m pytest tests/
```
