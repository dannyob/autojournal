# AutoJournal Makefile
# Common development and usage tasks

.PHONY: help install test run clean lint format check dev-install

# Default target
help:
	@echo "AutoJournal - Available Commands:"
	@echo ""
	@echo "Setup:"
	@echo "  install      Install dependencies using uv"
	@echo "  dev-install  Install development dependencies"
	@echo ""
	@echo "Development:"
	@echo "  test         Run all tests"
	@echo "  test-v       Run tests with verbose output"
	@echo "  lint         Run code linting (if ruff available)"
	@echo "  format       Format code (if ruff available)"
	@echo "  check        Run all checks (tests + lint)"
	@echo ""
	@echo "Usage:"
	@echo "  run          Run AutoJournal with default goals.md"
	@echo "  run-custom   Run with custom goals file (make run-custom GOALS=mygoals.md)"
	@echo "  demo         Run with sample goals"
	@echo ""
	@echo "Maintenance:"
	@echo "  clean        Clean temporary files and caches"
	@echo "  reset-task   Remove current task display file"
	@echo "  backup       Backup journal files"

# Installation
install:
	@echo "Installing AutoJournal dependencies..."
	uv add llm textual pillow pytest pytest-asyncio

dev-install: install
	@echo "Installing development dependencies..."
	uv add --dev ruff black isort mypy
	@echo "Development environment ready!"

# Testing
test:
	@echo "Running AutoJournal tests..."
	uv run python -m pytest tests/

test-v:
	@echo "Running AutoJournal tests (verbose)..."
	uv run python -m pytest tests/ -v

# Code quality
lint:
	@echo "Running code linter..."
	@if command -v ruff >/dev/null 2>&1; then \
		uv run ruff check autojournal/ tests/; \
	else \
		echo "ruff not installed - run 'make dev-install' first"; \
	fi

format:
	@echo "Formatting code..."
	@if command -v ruff >/dev/null 2>&1; then \
		uv run ruff format autojournal/ tests/; \
	else \
		echo "ruff not installed - run 'make dev-install' first"; \
	fi

check: test lint
	@echo "All checks completed!"

# Usage
run:
	@echo "Starting AutoJournal with goals.md..."
	@if [ ! -f goals.md ]; then \
		echo "No goals.md found. Creating sample goals file..."; \
		make demo-goals; \
	fi
	uv run python autojournal.py goals.md

run-custom:
	@if [ -z "$(GOALS)" ]; then \
		echo "Usage: make run-custom GOALS=your-goals.md"; \
		exit 1; \
	fi
	@if [ ! -f "$(GOALS)" ]; then \
		echo "Goals file '$(GOALS)' not found!"; \
		exit 1; \
	fi
	@echo "Starting AutoJournal with $(GOALS)..."
	uv run python autojournal.py $(GOALS)

demo:
	@echo "Creating demo goals and running AutoJournal..."
	@make demo-goals
	@echo "Demo goals created in goals.md"
	@echo "Starting AutoJournal in 3 seconds..."
	@sleep 3
	uv run python autojournal.py goals.md

demo-goals:
	@echo "Creating sample goals.md..."
	@echo "# Complete Today's Work Tasks" > goals.md
	@echo "" >> goals.md
	@echo "Finish the high-priority work items on my todo list and prepare for tomorrow's meetings." >> goals.md
	@echo "" >> goals.md
	@echo "# Learn Something New" >> goals.md
	@echo "" >> goals.md
	@echo "Spend time learning a new technology, reading documentation, or watching educational content." >> goals.md
	@echo "" >> goals.md
	@echo "# Exercise and Health" >> goals.md
	@echo "" >> goals.md
	@echo "Take breaks for physical activity, stretching, or a short walk to maintain energy levels." >> goals.md
	@echo "" >> goals.md
	@echo "# Personal Project Time" >> goals.md
	@echo "" >> goals.md
	@echo "Work on a personal coding project or hobby to maintain creativity and skill development." >> goals.md
	@echo "Sample goals.md created!"

# Maintenance
clean:
	@echo "Cleaning temporary files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.log" -delete
	rm -rf .coverage htmlcov/
	@echo "Cleanup completed!"

reset-task:
	@echo "Removing current task display file..."
	@if [ -f ~/.current-task ]; then \
		rm ~/.current-task; \
		echo "Current task file removed."; \
	else \
		echo "No current task file found."; \
	fi

backup:
	@echo "Backing up journal files..."
	@mkdir -p backups
	@if ls journal-*.md >/dev/null 2>&1; then \
		cp journal-*.md backups/; \
		echo "Journal files backed up to backups/"; \
	else \
		echo "No journal files found to backup."; \
	fi

# Development helpers
dev-setup: dev-install
	@echo "Setting up development environment..."
	@echo "Creating .vscode/settings.json for optimal development..."
	@mkdir -p .vscode
	@echo '{' > .vscode/settings.json
	@echo '    "python.defaultInterpreterPath": ".venv/bin/python",' >> .vscode/settings.json
	@echo '    "python.testing.pytestEnabled": true,' >> .vscode/settings.json
	@echo '    "python.testing.pytestArgs": ["tests/"],' >> .vscode/settings.json
	@echo '    "python.linting.enabled": true,' >> .vscode/settings.json
	@echo '    "python.linting.ruffEnabled": true,' >> .vscode/settings.json
	@echo '    "python.formatting.provider": "ruff",' >> .vscode/settings.json
	@echo '    "editor.formatOnSave": true,' >> .vscode/settings.json
	@echo '    "editor.rulers": [88],' >> .vscode/settings.json
	@echo '    "files.exclude": {' >> .vscode/settings.json
	@echo '        "**/__pycache__": true,' >> .vscode/settings.json
	@echo '        "**/*.pyc": true,' >> .vscode/settings.json
	@echo '        ".pytest_cache": true' >> .vscode/settings.json
	@echo '    }' >> .vscode/settings.json
	@echo '}' >> .vscode/settings.json
	@echo "VS Code settings configured!"
	@echo "Development environment ready!"

# Quick status check
status:
	@echo "AutoJournal Status:"
	@echo "==================="
	@echo "Current directory: $(PWD)"
	@echo "Python version: $(shell python3 --version 2>/dev/null || echo 'Not found')"
	@echo "UV installed: $(shell command -v uv >/dev/null 2>&1 && echo 'Yes' || echo 'No')"
	@echo "Goals file exists: $(shell [ -f goals.md ] && echo 'Yes' || echo 'No')"
	@echo "Current task active: $(shell [ -f ~/.current-task ] && echo 'Yes' || echo 'No')"
	@echo "Journal files: $(shell ls journal-*.md 2>/dev/null | wc -l | tr -d ' ') found"
	@echo "Tests status: $(shell uv run python -m pytest tests/ --tb=no -q 2>/dev/null | tail -1 || echo 'Run make test to check')"