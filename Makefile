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
	@echo "  lint         Run code linting"
	@echo "  format       Format code"
	@echo "  check        Run all checks (tests + lint)"
	@echo ""
	@echo "Usage:"
	@echo "  run          Run AutoJournal (make run ARGS='--debug goals.md')"
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
	@uv run ruff check autojournal/ tests/ || echo "Install dev dependencies with 'make dev-install'"

format:
	@echo "Formatting code..."
	@uv run ruff format autojournal/ tests/ || echo "Install dev dependencies with 'make dev-install'"

check: test lint
	@echo "All checks completed!"

# Usage - supports passing arguments via ARGS variable
run:
	@echo "Starting AutoJournal..."
	@if [ -z "$(ARGS)" ] && [ ! -f goals.md ]; then \
		echo "No goals.md found. Creating sample goals file..."; \
		$(MAKE) -s _create-demo-goals; \
		uv run python autojournal.py goals.md; \
	elif [ -z "$(ARGS)" ]; then \
		uv run python autojournal.py goals.md; \
	else \
		uv run python autojournal.py $(ARGS); \
	fi

demo: _create-demo-goals
	@echo "Demo goals created in goals.md"
	@echo "Starting AutoJournal..."
	uv run python autojournal.py goals.md

# Internal target for creating demo goals
_create-demo-goals:
	@echo "# Complete Today's Work Tasks\n\nFinish the high-priority work items on my todo list and prepare for tomorrow's meetings.\n\n# Learn Something New\n\nSpend time learning a new technology, reading documentation, or watching educational content.\n\n# Exercise and Health\n\nTake breaks for physical activity, stretching, or a short walk to maintain energy levels.\n\n# Personal Project Time\n\nWork on a personal coding project or hobby to maintain creativity and skill development." > goals.md

# Maintenance
clean:
	@echo "Cleaning temporary files..."
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name "__pycache__" -delete
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.log" -delete
	@rm -rf .coverage htmlcov/
	@echo "Cleanup completed!"

reset-task:
	@echo "Removing current task display file..."
	@rm -f ~/.current-task && echo "Current task file removed." || echo "No current task file found."

backup:
	@echo "Backing up journal files..."
	@mkdir -p backups
	@cp journal-*.md backups/ 2>/dev/null && echo "Journal files backed up to backups/" || echo "No journal files found to backup."

# Development helpers
dev-setup: dev-install
	@echo "Setting up development environment..."
	@mkdir -p .vscode
	@printf '{\n  "python.defaultInterpreterPath": ".venv/bin/python",\n  "python.testing.pytestEnabled": true,\n  "python.testing.pytestArgs": ["tests/"],\n  "python.linting.enabled": true,\n  "python.linting.ruffEnabled": true,\n  "python.formatting.provider": "ruff",\n  "editor.formatOnSave": true,\n  "editor.rulers": [88],\n  "files.exclude": {\n    "**/__pycache__": true,\n    "**/*.pyc": true,\n    ".pytest_cache": true\n  }\n}' > .vscode/settings.json
	@echo "Development environment ready!"

# Quick status check
status:
	@echo "AutoJournal Status:"
	@echo "==================="
	@echo "Current directory: $$(pwd)"
	@echo "Python version: $$(python3 --version 2>/dev/null || echo 'Not found')"
	@echo "UV installed: $$(command -v uv >/dev/null 2>&1 && echo 'Yes' || echo 'No')"
	@echo "Goals file exists: $$([ -f goals.md ] && echo 'Yes' || echo 'No')"
	@echo "Current task active: $$([ -f ~/.current-task ] && echo 'Yes' || echo 'No')"
	@echo "Journal files: $$(ls journal-*.md 2>/dev/null | wc -l | tr -d ' ') found"