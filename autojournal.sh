#!/bin/bash
# AutoJournal wrapper script that properly manages terminal state

# Function to disable mouse tracking
disable_mouse() {
    printf '\033[?1000l'  # Disable basic mouse tracking
    printf '\033[?1003l'  # Disable all mouse tracking
    printf '\033[?1015l'  # Disable extended mouse tracking
    printf '\033[?1006l'  # Disable SGR mouse tracking
}

# Set up cleanup on exit
trap disable_mouse EXIT

# Run the Python application
python3 "$(dirname "$0")/autojournal.py" "$@"

# Ensure cleanup happens
disable_mouse